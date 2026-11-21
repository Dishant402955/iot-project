#pragma once
#include <string>
#include <cstdint>
namespace wifisense { struct SignalSample { std::int64_t timestamp_ms{}; int signal_percent{}; std::string interface_name, network_name; int label{-1}; }; }
