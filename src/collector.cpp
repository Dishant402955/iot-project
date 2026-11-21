#include "wifisense/collector.hpp"
#include "wifisense/linux_wifi.hpp"
#include "wifisense/csv_writer.hpp"
#include "wifisense/features.hpp"
#include "wifisense/anomaly_detector.hpp"
#include "wifisense/clock.hpp"
#include <chrono>
#include <csignal>
#include <iostream>
#include <thread>
#include <vector>
namespace wifisense {
namespace {volatile std::sig_atomic_t stopped=0;void stop_handler(int){stopped=1;}}
int inspect(const Config&c){try{auto s=LinuxWifi(c.interface_name).sample();std::cout<<"Interface: "<<s.interface_name<<"\nNetwork (SSID): "<<s.network_name<<"\nSignal: "<<s.signal_percent<<"%\nMeasurement: NetworkManager signal percentage (not CSI; scan-cache based).\n";return 0;}catch(const std::exception&e){std::cerr<<"Error: "<<e.what()<<'\n';return 1;}}
int collect(const Config&c,int label,int seconds,const char*path){if(label<0||label>5||seconds<1){std::cerr<<"Label must be 0..5 and seconds positive.\n";return 2;}try{CsvWriter w(path);LinuxWifi wifi(c.interface_name);auto end=std::chrono::steady_clock::now()+std::chrono::seconds(seconds);std::cout<<"Collecting label="<<label<<" for "<<seconds<<" seconds. Ctrl+C stops.\n";while(!stopped&&std::chrono::steady_clock::now()<end){auto s=wifi.sample();s.label=label;w.write(s);std::cout<<iso_timestamp()<<" Signal "<<s.signal_percent<<"%\n";std::this_thread::sleep_for(std::chrono::milliseconds(c.interval_ms));}std::cout<<"Capture finished: "<<path<<'\n';return 0;}catch(const std::exception&e){std::cerr<<"Error: "<<e.what()<<'\n';return 1;}}
int monitor(const Config&c){try{LinuxWifi wifi(c.interface_name);std::vector<double>r;AnomalyDetector detector;std::signal(SIGINT,stop_handler);std::cout<<"Signal disturbance monitor. First rolling window is baseline. Ctrl+C exits.\n";while(!stopped){auto s=wifi.sample();r.push_back(s.signal_percent);if(static_cast<int>(r.size())>c.window_size){r.erase(r.begin());}if(static_cast<int>(r.size())==c.window_size){auto f=extract_features(r);if(!detector.calibrated()){detector.calibrate(f);std::cout<<"Baseline initialized.\n";}else{double score=detector.score(f);std::cout<<iso_timestamp()<<" Signal="<<s.signal_percent<<"% disturbance_score="<<score<<(score>=35?" [SIGNAL CHANGE]":" [STABLE-ISH]")<<'\n';}}else std::cout<<"Warming up "<<r.size()<<'/'<<c.window_size<<'\n';std::this_thread::sleep_for(std::chrono::milliseconds(c.interval_ms));}return 0;}catch(const std::exception&e){std::cerr<<"Error: "<<e.what()<<'\n';return 1;}}
}
