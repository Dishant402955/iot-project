#include "wifisense/features.hpp"
#include "wifisense/anomaly_detector.hpp"
#include <cassert>
#include <iostream>
int main(){using namespace wifisense;auto f=extract_features({40,40,39,40,40});assert(f.mean_signal<40&&f.mean_signal>39);assert(f.stddev_signal>0);assert(f.min_signal==39&&f.max_signal==40);AnomalyDetector d;assert(!d.calibrated());d.calibrate(f);assert(d.calibrated());auto changed=extract_features({40,25,45,20,50});assert(d.score(changed)>0);assert(d.score(f)==0);std::cout<<"All tests passed.\n";}
