from __future__ import annotations

import os
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


def latest_raw_run(raw_base_dir: Path) -> Path:
    runs = [p for p in raw_base_dir.iterdir() if p.is_dir()]
    if not runs:
        raise FileNotFoundError(f"No hay carpetas raw en {raw_base_dir}")
    return sorted(runs, key=lambda p: p.name)[-1]


def build_spark() -> SparkSession:
    return (
        SparkSession.builder.appName("space-launches-silver-gold")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "200")
        .getOrCreate()
    )


def write_parquet(df: DataFrame, path: Path, partition_cols: list[str] | None = None) -> None:
    writer = df.write.mode("overwrite").format("parquet")
    if partition_cols:
        writer = writer.partitionBy(*partition_cols)
    writer.save(str(path))


def build_silver_launches(spark: SparkSession, raw_run_path: Path) -> DataFrame:
    launches = spark.read.json(str(raw_run_path / "launch_library_launches.jsonl"))

    return (
        launches.select(
            F.col("id").alias("launch_id"),
            F.col("name").alias("launch_name"),
            F.col("net").alias("launch_net_utc"),
            F.col("status.id").cast("int").alias("status_id"),
            F.col("status.name").alias("status_name"),
            F.col("status.abbrev").alias("status_abbrev"),
            F.col("launch_service_provider.id").cast("int").alias("provider_id"),
            F.col("launch_service_provider.name").alias("provider_name"),
            F.col("rocket.id").cast("int").alias("rocket_internal_id"),
            F.col("rocket.configuration.id").cast("int").alias("rocket_config_id"),
            F.col("rocket.configuration.name").alias("rocket_name"),
            F.col("rocket.configuration.family").alias("rocket_family"),
            F.col("mission.id").cast("int").alias("mission_id"),
            F.col("mission.name").alias("mission_name"),
            F.col("mission.type").alias("mission_type"),
            F.col("mission.orbit.name").alias("mission_orbit"),
            F.col("pad.id").cast("int").alias("pad_id"),
            F.col("pad.name").alias("pad_name"),
            F.col("pad.country_code").alias("pad_country_code"),
            F.col("pad.latitude").cast("double").alias("pad_latitude"),
            F.col("pad.longitude").cast("double").alias("pad_longitude"),
            F.col("pad.location.name").alias("location_name"),
            F.col("pad.location.country_code").alias("location_country_code"),
            F.col("type").alias("launch_type"),
        )
        .withColumn("launch_ts", F.to_timestamp("launch_net_utc"))
        .withColumn("launch_date", F.to_date("launch_ts"))
        .withColumn("launch_year", F.year("launch_date"))
        .withColumn(
            "is_success",
            F.when(F.lower(F.col("status_abbrev")).contains("success"), F.lit(1)).otherwise(F.lit(0)),
        )
        .filter(F.col("launch_id").isNotNull())
    )


def build_silver_weather(spark: SparkSession, raw_run_path: Path) -> DataFrame:
    weather = spark.read.json(str(raw_run_path / "open_meteo_samples.jsonl"))

    return (
        weather.select(
            F.col("launch_id"),
            F.col("date").alias("weather_date_raw"),
            F.col("latitude").cast("double").alias("weather_latitude"),
            F.col("longitude").cast("double").alias("weather_longitude"),
            F.col("weather.timezone").alias("weather_timezone"),
            F.col("weather.elevation").cast("double").alias("weather_elevation"),
            F.element_at(F.col("weather.daily.temperature_2m_mean"), 1)
            .cast("double")
            .alias("temperature_2m_mean"),
            F.element_at(F.col("weather.daily.wind_speed_10m_max"), 1)
            .cast("double")
            .alias("wind_speed_10m_max"),
        )
        .withColumn("weather_date", F.to_date("weather_date_raw"))
        .withColumn("weather_year", F.year("weather_date"))
        .filter(F.col("launch_id").isNotNull())
    )


def build_silver_rockets(spark: SparkSession, raw_run_path: Path) -> DataFrame:
    rockets = spark.read.option("multiline", "true").json(
        str(raw_run_path / "spacex_rockets.json")
    )

    return rockets.select(
        F.col("id").alias("spacex_rocket_id"),
        F.col("name").alias("rocket_name"),
        F.col("type").alias("rocket_type"),
        F.col("active").cast("boolean").alias("is_active"),
        F.col("stages").cast("int").alias("stages"),
        F.col("boosters").cast("int").alias("boosters"),
        F.col("cost_per_launch").cast("long").alias("cost_per_launch_usd"),
        F.col("success_rate_pct").cast("double").alias("success_rate_pct"),
        F.col("first_flight").alias("first_flight_date"),
        F.col("country").alias("country"),
        F.col("company").alias("company"),
        F.col("height.meters").cast("double").alias("height_meters"),
        F.col("diameter.meters").cast("double").alias("diameter_meters"),
        F.col("mass.kg").cast("double").alias("mass_kg"),
        F.col("description").alias("description"),
        F.col("wikipedia").alias("wikipedia_url"),
    )


def build_silver_images(spark: SparkSession, raw_run_path: Path) -> DataFrame:
    ll_images_raw = spark.read.json(str(raw_run_path / "launch_library_images.jsonl"))
    spacex_images_raw = spark.read.json(str(raw_run_path / "spacex_launches_images.jsonl"))

    ll_images = (
        ll_images_raw.select(
            F.lit("launch_library").alias("source"),
            F.col("launch_library_id").alias("launch_id"),
            F.col("name").alias("launch_name"),
            F.col("net").alias("launch_datetime_utc"),
            F.explode_outer(
                F.array_distinct(
                    F.filter(F.array(F.col("image"), F.col("infographic")), lambda x: x.isNotNull())
                )
            ).alias("image_url"),
        )
        .filter(F.col("image_url").isNotNull())
        .withColumn("launch_date", F.to_date(F.to_timestamp("launch_datetime_utc")))
        .withColumn("launch_year", F.year("launch_date"))
    )

    spacex_images = (
        spacex_images_raw.select(
            F.lit("spacex").alias("source"),
            F.col("spacex_launch_id").alias("launch_id"),
            F.col("name").alias("launch_name"),
            F.col("date_utc").alias("launch_datetime_utc"),
            F.explode_outer("image_urls").alias("image_url"),
        )
        .filter(F.col("image_url").isNotNull())
        .withColumn("launch_date", F.to_date(F.to_timestamp("launch_datetime_utc")))
        .withColumn("launch_year", F.year("launch_date"))
    )

    return ll_images.unionByName(spacex_images)


def build_silver_launch_costs(launches_silver: DataFrame) -> DataFrame:
    """Generate synthetic launch costs from silver launches using known rocket cost references."""
    rocket_costs = {
        "Falcon 9":        (62_000_000, 2720,  "Standard"),
        "Falcon Heavy":    (90_000_000, 1410,  "Heavy"),
        "Starship":        (10_000_000, 100,   "Heavy"),
        "Falcon 1":        (7_000_000,  4109,  "Budget"),
        "Ariane 5":        (165_000_000,10500, "Premium"),
        "Ariane 6":        (75_000_000, 4500,  "Standard"),
        "Atlas V":         (130_000_000,8000,  "Premium"),
        "Delta IV Heavy":  (350_000_000,13000, "Premium"),
        "Vulcan Centaur":  (110_000_000,5600,  "Standard"),
        "Soyuz-2":         (55_000_000, 7000,  "Standard"),
        "Proton-M":        (65_000_000, 4600,  "Standard"),
        "PSLV":            (15_000_000, 1500,  "Budget"),
        "GSLV":            (45_000_000, 2500,  "Standard"),
        "GSLV Mk III":     (48_000_000, 2600,  "Standard"),
        "H-IIA":           (90_000_000, 8400,  "Premium"),
        "H3":              (50_000_000, 5500,  "Standard"),
        "Long March 2D":   (30_000_000, 2000,  "Budget"),
        "Long March 3B":   (55_000_000, 5000,  "Standard"),
        "Long March 5":    (70_000_000, 2500,  "Standard"),
        "Electron":        (7_500_000,  35714, "Budget"),
        "Antares":         (85_000_000, 8000,  "Standard"),
        "Pegasus":         (40_000_000, 75000, "Budget"),
        "New Glenn":       (60_000_000, 2500,  "Standard"),
        "Vega":            (37_000_000, 3600,  "Budget"),
        "Vega-C":          (42_000_000, 3000,  "Budget"),
    }

    cost_map_rows = [
        (name, base, cpkg, cat)
        for name, (base, cpkg, cat) in rocket_costs.items()
    ]
    spark = launches_silver.sparkSession
    cost_schema_df = spark.createDataFrame(
        cost_map_rows,
        schema=["rocket_name", "_base_cost", "_cost_per_kg", "_category"],
    )

    df = (
        launches_silver.alias("l")
        .join(cost_schema_df.alias("c"), F.col("l.rocket_name") == F.col("c.rocket_name"), "left")
        .select(
            F.col("l.launch_id"),
            F.col("l.rocket_name"),
            F.col("l.provider_name"),
            F.col("l.launch_year"),
            F.col("l.mission_type"),
            F.col("l.is_success"),
            F.coalesce(F.col("c._base_cost"), F.lit(50_000_000)).cast("long").alias("estimated_cost_usd"),
            F.coalesce(F.col("c._cost_per_kg"), F.lit(5000)).cast("long").alias("cost_per_kg_leo_usd"),
            F.coalesce(F.col("c._category"), F.lit("Standard")).alias("cost_category"),
        )
    )
    return df


def build_gold_company_year_metrics(launches_silver: DataFrame) -> DataFrame:
    return launches_silver.groupBy("launch_year", "provider_name").agg(
        F.count("launch_id").alias("total_launches"),
        F.sum("is_success").alias("successful_launches"),
        F.round((F.sum("is_success") / F.count("launch_id")) * 100, 2).alias("success_rate_pct"),
    )


def build_gold_launch_features(
    launches_silver: DataFrame, weather_silver: DataFrame, images_silver: DataFrame
) -> DataFrame:
    image_counts = images_silver.groupBy("source", "launch_id").agg(
        F.count("image_url").alias("image_count")
    )

    launch_library_image_counts = image_counts.filter(F.col("source") == "launch_library").select(
        "launch_id", F.col("image_count").alias("launch_image_count")
    )

    return (
        launches_silver.alias("l")
        .join(weather_silver.alias("w"), F.col("l.launch_id") == F.col("w.launch_id"), "left")
        .join(
            launch_library_image_counts.alias("i"),
            F.col("l.launch_id") == F.col("i.launch_id"),
            "left",
        )
        .select(
            F.col("l.launch_id"),
            F.col("l.launch_name"),
            F.col("l.launch_date"),
            F.col("l.launch_year"),
            F.col("l.provider_name"),
            F.col("l.rocket_name"),
            F.col("l.mission_type"),
            F.col("l.mission_orbit"),
            F.col("l.pad_country_code"),
            F.col("l.pad_latitude"),
            F.col("l.pad_longitude"),
            F.col("l.is_success"),
            F.col("w.temperature_2m_mean"),
            F.col("w.wind_speed_10m_max"),
            F.coalesce(F.col("i.launch_image_count"), F.lit(0)).alias("launch_image_count"),
        )
    )


def main() -> None:
    raw_base_dir = Path(os.getenv("RAW_BASE_DIR", "/opt/bitnami/spark/workspace/data/raw"))
    silver_base_dir = Path(
        os.getenv("SILVER_BASE_DIR", "/opt/bitnami/spark/workspace/data/silver")
    )
    gold_base_dir = Path(os.getenv("GOLD_BASE_DIR", "/opt/bitnami/spark/workspace/data/gold"))
    raw_run_id = os.getenv("RAW_RUN_ID", "").strip()

    raw_run_path = raw_base_dir / raw_run_id if raw_run_id else latest_raw_run(raw_base_dir)

    print(f"[processing] RAW run seleccionado: {raw_run_path}")

    spark = build_spark()

    launches_silver = build_silver_launches(spark, raw_run_path)
    weather_silver = build_silver_weather(spark, raw_run_path)
    rockets_silver = build_silver_rockets(spark, raw_run_path)
    images_silver = build_silver_images(spark, raw_run_path)

    write_parquet(launches_silver, silver_base_dir / "launches", ["launch_year"])
    write_parquet(weather_silver, silver_base_dir / "weather", ["weather_year"])
    write_parquet(rockets_silver, silver_base_dir / "spacex_rockets")
    write_parquet(images_silver, silver_base_dir / "images", ["source", "launch_year"])

    launch_costs_silver = build_silver_launch_costs(launches_silver)
    write_parquet(launch_costs_silver, silver_base_dir / "launch_costs", ["launch_year"])

    company_year_gold = build_gold_company_year_metrics(launches_silver)
    launch_features_gold = build_gold_launch_features(launches_silver, weather_silver, images_silver)

    write_parquet(company_year_gold, gold_base_dir / "company_year_metrics", ["launch_year"])
    write_parquet(launch_features_gold, gold_base_dir / "launch_features", ["launch_year"])

    print("[processing] Silver y Gold generados correctamente.")
    spark.stop()


if __name__ == "__main__":
    main()
