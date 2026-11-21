#include "wifisense/features.hpp"
#include <algorithm>
#include <cmath>
#include <numeric>
namespace wifisense {
namespace {double mean(const std::vector<double>&v){return v.empty()?0.0:std::accumulate(v.begin(),v.end(),0.0)/v.size();} double sd(const std::vector<double>&v){if(v.size()<2)return 0;double m=mean(v),s=0;for(double x:v)s+=(x-m)*(x-m);return std::sqrt(s/v.size());}}
SignalFeatures extract_features(const std::vector<double>&v){SignalFeatures f{};if(v.empty())return f;f.mean_signal=mean(v);f.stddev_signal=sd(v);auto b=std::minmax_element(v.begin(),v.end());f.min_signal=*b.first;f.max_signal=*b.second;std::vector<double>d;for(std::size_t i=1;i<v.size();++i)d.push_back(std::abs(v[i]-v[i-1]));f.mean_abs_delta=mean(d);return f;}
}
