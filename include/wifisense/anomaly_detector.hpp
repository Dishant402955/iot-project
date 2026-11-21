#pragma once
#include "wifisense/features.hpp"
namespace wifisense { class AnomalyDetector { public: void calibrate(const SignalFeatures&); double score(const SignalFeatures&) const; bool calibrated() const; private: SignalFeatures baseline_{}; bool calibrated_{false}; }; }
