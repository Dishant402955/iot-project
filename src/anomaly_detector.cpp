#include "wifisense/anomaly_detector.hpp"
#include <algorithm>
#include <cmath>
namespace wifisense {
void AnomalyDetector::calibrate(const SignalFeatures&f){baseline_=f;calibrated_=true;}
double AnomalyDetector::score(const SignalFeatures&f)const{if(!calibrated_)return 0;double v=std::max(0.5,baseline_.stddev_signal),d=std::max(0.5,baseline_.mean_abs_delta);double a=std::abs(f.stddev_signal-baseline_.stddev_signal)/v,b=std::abs(f.mean_abs_delta-baseline_.mean_abs_delta)/d;return std::min(100.0,50.0*(a+b));}
bool AnomalyDetector::calibrated()const{return calibrated_;}
}
