#include "wifisense/clock.hpp"
#include <chrono>
#include <ctime>
#include <iomanip>
#include <sstream>
namespace wifisense {
std::int64_t unix_time_ms() { return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count(); }
std::string iso_timestamp() { const auto now=std::chrono::system_clock::now(); const auto t=std::chrono::system_clock::to_time_t(now); std::tm tm{}; localtime_r(&t,&tm); std::ostringstream o; o<<std::put_time(&tm,"%Y-%m-%dT%H:%M:%S"); return o.str(); }
}
