INSERT INTO stg.orders_n_weather(
    CityId, CityName, CityTimeZone, WeatherTime, OrderId, UserId, OrderStatus,
    RestaurantId, Temperature, RelativeHumidity, Precipitation, Rain, Snowfall,
    SnowDepth, WeatherCode, PressureMSL, SurfacePressure, CloudCover,
    WindSpeed, WindDirection, Latitude, Longitude, AddedOn
    )
SELECT
    o.CityId, c.Name, c.TimeZone, w.WeatherTime, o.Id, o.UserId, o.Status,
    o.RestaurantId, w.Temperature, w.RelativeHumidity, w.Precipitation, w.Rain, w.Snowfall,
    w.SnowDepth, w.WeatherCode, w.PressureMSL, w.SurfacePressure, w.CloudCover,
    w.WindSpeed, w.WindDirection, w.Latitude, w.Longitude, SYSDATETIMEOFFSET()
FROM prod.dbo.orders o
INNER JOIN prod.dbo.cities c
    ON c.Id = o.CityId
INNER JOIN test_user_7.dm.weather_series w
    ON w.CityId = o.CityId
    AND w.WeatherTime = FORMAT(o.AddedOn, 'yyyy-MM-dd HH:00:00')
WHERE o.AddedOn BETWEEN :start_date AND DATEADD(day, 1, :end_date)