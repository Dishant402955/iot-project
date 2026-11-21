#pragma once
#include <vector>
namespace wifisense { struct SignalFeatures { double mean_signal{}, stddev_signal{}, min_signal{}, max_signal{}, mean_abs_delta{}; }; SignalFeatures extract_features(const std::vector<double>&); }
