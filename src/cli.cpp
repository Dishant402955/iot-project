#include "wifisense/cli.hpp"
#include "wifisense/collector.hpp"
#include "wifisense/config.hpp"
#include <iostream>
#include <string>
namespace wifisense {
namespace {void help(){std::cout<<"Wi-Fi Presence Lab (signal-strength prototype)\n  wifi_sense inspect [--interface IFACE]\n  wifi_sense collect --label 0..5 --seconds N --output FILE [--interface IFACE]\n  wifi_sense monitor [--interface IFACE]\nLabels: 0=empty, 1..5=ground-truth people present.\nThis build measures connected-network signal percentage, not CSI; it does not estimate a headcount.\n";}}
int run_cli(int argc,char**argv){if(argc<2){help();return 0;}std::string mode=argv[1];Config c;int label=-1,seconds=60;std::string output="data/capture.csv";for(int i=2;i<argc;++i){std::string k=argv[i];if(k=="--interface"&&i+1<argc)c.interface_name=argv[++i];else if(k=="--label"&&i+1<argc)label=std::stoi(argv[++i]);else if(k=="--seconds"&&i+1<argc)seconds=std::stoi(argv[++i]);else if(k=="--output"&&i+1<argc)output=argv[++i];else{std::cerr<<"Unknown/incomplete option: "<<k<<'\n';help();return 2;}}if(mode=="inspect")return inspect(c);if(mode=="collect")return collect(c,label,seconds,output.c_str());if(mode=="monitor")return monitor(c);if(mode=="help"||mode=="--help"){help();return 0;}std::cerr<<"Unknown mode: "<<mode<<'\n';help();return 2;}
}
