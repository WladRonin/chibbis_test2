IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'stg')
BEGIN
    EXEC('CREATE SCHEMA stg');
END;

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'raw')
BEGIN
    EXEC('CREATE SCHEMA raw');
END;

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'dm')
BEGIN
    EXEC('CREATE SCHEMA dm');
END;

DROP TABLE IF EXISTS raw.weather_series;
CREATE TABLE raw.weather_series (
    CityId VARCHAR(250),
    WeatherTime DATETIME,
    temperature_2m DECIMAL(5, 2),
    relative_humidity_2m TINYINT,
    precipitation DECIMAL(5, 2),
    rain DECIMAL(5, 2),
    snowfall DECIMAL(5, 2),
    snow_depth DECIMAL(5, 2),
    weather_code VARCHAR(250),
    pressure_msl DECIMAL(6, 2),
    surface_pressure DECIMAL(6, 2),
    cloud_cover TINYINT,
    wind_speed_10m DECIMAL(5, 2),
    wind_direction_10m SMALLINT,
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    SourceSystem VARCHAR(100) NOT NULL DEFAULT 'https://archive-api.open-meteo.com',
    AddedOn DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET()
);

DROP TABLE IF EXISTS stg.weather_series;
CREATE TABLE stg.weather_series (
    CityId UNIQUEIDENTIFIER,
    WeatherTime DATETIME,
    temperature_2m DECIMAL(5, 2),
    relative_humidity_2m TINYINT,
    precipitation DECIMAL(5, 2),
    rain DECIMAL(5, 2),
    snowfall DECIMAL(5, 2),
    snow_depth DECIMAL(5, 2),
    weather_code VARCHAR(250),
    pressure_msl DECIMAL(6, 2),
    surface_pressure DECIMAL(6, 2),
    cloud_cover TINYINT,
    wind_speed_10m DECIMAL(5, 2),
    wind_direction_10m SMALLINT,
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    SourceSystem VARCHAR(100) NOT NULL,
    AddedOn DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    HashKey AS HASHBYTES(
        'SHA2_256', 
        CONCAT_WS('|', WeatherTime, STR(latitude, 10, 7), STR(longitude, 10, 7))
    ) PERSISTED,
    INDEX idx_stg_weather_series NONCLUSTERED (HashKey)
);

DROP TABLE IF EXISTS dm.weather_series;
CREATE TABLE dm.weather_series (
    CityId UNIQUEIDENTIFIER NOT NULL,
    WeatherTime DATETIME,
    Temperature DECIMAL(5, 2),
    RelativeHumidity TINYINT,
    Precipitation DECIMAL(5, 2),
    Rain DECIMAL(5, 2),
    Snowfall DECIMAL(5, 2),
    SnowDepth DECIMAL(5, 2),
    WeatherCode VARCHAR(250),
    PressureMSL DECIMAL(6, 2),
    SurfacePressure DECIMAL(6, 2),
    CloudCover TINYINT,
    WindSpeed DECIMAL(5, 2),
    WindDirection SMALLINT,
    Latitude DECIMAL(10, 7),
    Longitude DECIMAL(10, 7),
    SourceSystem VARCHAR(100),
    AddedOn DATETIMEOFFSET NOT NULL,
    HashKey AS HASHBYTES(
        'SHA2_256', 
        CONCAT_WS('|', WeatherTime, STR(Latitude, 10, 7), STR(Longitude, 10, 7))
    ) PERSISTED,
    ChangedOn DATETIMEOFFSET NOT NULL,
    CONSTRAINT pk_weather_series PRIMARY KEY NONCLUSTERED (HashKey),
    INDEX idx_weather_series CLUSTERED (WeatherTime)
);

DROP TABLE IF EXISTS stg.orders_n_weather;
CREATE TABLE stg.orders_n_weather (
    CityId UNIQUEIDENTIFIER NOT NULL,
    CityName NVARCHAR(50) COLLATE Cyrillic_General_CI_AS NOT NULL, 
    CityTimeZone INTEGER NOT NULL, 
    WeatherTime DATETIME NOT NULL,
    OrderId UNIQUEIDENTIFIER NOT NULL,
    UserId UNIQUEIDENTIFIER NOT NULL,
    OrderStatus INTEGER NOT NULL,
    RestaurantId UNIQUEIDENTIFIER NOT NULL,
    Temperature DECIMAL(5, 2),
    RelativeHumidity TINYINT,
    Precipitation DECIMAL(5, 2),
    Rain DECIMAL(5, 2),
    Snowfall DECIMAL(5, 2),
    SnowDepth DECIMAL(5, 2),
    WeatherCode VARCHAR(250),
    PressureMSL DECIMAL(6, 2),
    SurfacePressure DECIMAL(6, 2),
    CloudCover TINYINT,
    WindSpeed DECIMAL(5, 2),
    WindDirection SMALLINT,
    Latitude DECIMAL(10, 7),
    Longitude DECIMAL(10, 7),
    AddedOn DATETIMEOFFSET NOT NULL DEFAULT SYSDATETIMEOFFSET(),
    HashKey AS HASHBYTES(
        'SHA2_256', 
        CONCAT_WS('|', WeatherTime, CityId, OrderId)
    ) PERSISTED,
    INDEX idx_stg_orders_n_weather NONCLUSTERED (HashKey)
);

DROP TABLE IF EXISTS dm.orders_n_weather;
CREATE TABLE dm.orders_n_weather (
    CityId UNIQUEIDENTIFIER NOT NULL,
    CityName NVARCHAR(50) COLLATE Cyrillic_General_CI_AS NOT NULL, 
    CityTimeZone INTEGER NOT NULL, 
    WeatherTime DATETIME NOT NULL,
    OrderId UNIQUEIDENTIFIER NOT NULL,
    UserId UNIQUEIDENTIFIER NOT NULL,
    OrderStatus INTEGER NOT NULL,
    RestaurantId UNIQUEIDENTIFIER NOT NULL,
    Temperature DECIMAL(5, 2),
    RelativeHumidity TINYINT,
    Precipitation DECIMAL(5, 2),
    Rain DECIMAL(5, 2),
    Snowfall DECIMAL(5, 2),
    SnowDepth DECIMAL(5, 2),
    WeatherCode VARCHAR(250),
    PressureMSL DECIMAL(6, 2),
    SurfacePressure DECIMAL(6, 2),
    CloudCover TINYINT,
    WindSpeed DECIMAL(5, 2),
    WindDirection SMALLINT,
    Latitude DECIMAL(10, 7),
    Longitude DECIMAL(10, 7),
    AddedOn DATETIMEOFFSET NOT NULL,
    HashKey AS HASHBYTES(
        'SHA2_256', 
        CONCAT_WS('|', WeatherTime, CityId, OrderId)
    ) PERSISTED,
    ChangedOn DATETIMEOFFSET NOT NULL,
    CONSTRAINT pk_orders_n_weather PRIMARY KEY NONCLUSTERED (HashKey),
    INDEX idx_orders_n_weather CLUSTERED (WeatherTime)
);

