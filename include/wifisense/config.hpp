#pragma once
#include <string>
namespace wifisense { struct Config { std::string interface_name{"wlp1s0"}; int interval_ms{1000}; int window_size{20}; int calibration_samples{30}; }; }
