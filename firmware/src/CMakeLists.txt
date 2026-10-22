idf_component_register(
  SRCS
    "main.cpp"
    "model.cpp"
    "renderer_core.cpp"
    "strict_json.cpp"
    "protocol_codec.cpp"
    "session_server.cpp"
    "device_io.cpp"
  INCLUDE_DIRS "../include"
  REQUIRES
    driver
    esp_adc
    esp_event
    esp_http_server
    esp_netif
    esp_timer
    esp_wifi
    mbedtls
    mdns
    nvs_flash
    json
  PRIV_REQUIRES esp_driver_rmt esp_driver_gpio
)

