#pragma once
#include "wifisense/signal_sample.hpp"
#include <string>
namespace wifisense { class LinuxWifi { public: explicit LinuxWifi(std::string); SignalSample sample() const; const std::string& interface_name() const; private: std::string interface_name_; }; }
