#include "wifisense/linux_wifi.hpp"
#include "wifisense/clock.hpp"
#include <cstdio>
#include <stdexcept>
#include <array>
#include <utility>
namespace wifisense {
LinuxWifi::LinuxWifi(std::string n):interface_name_(std::move(n)){}
const std::string& LinuxWifi::interface_name()const{return interface_name_;}
SignalSample LinuxWifi::sample()const{
 if(interface_name_.find_first_not_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")!=std::string::npos)throw std::runtime_error("Invalid interface name");
 const std::string cmd="nmcli -t --escape yes -f IN-USE,SSID,SIGNAL,FREQ dev wifi list --rescan no 2>/dev/null";
 FILE* p=popen(cmd.c_str(),"r");if(!p)throw std::runtime_error("Could not execute nmcli");
 std::string out;std::array<char,512>b{};while(fgets(b.data(),static_cast<int>(b.size()),p))out+=b.data();int status=pclose(p);
 if(status!=0||out.empty())throw std::runtime_error("nmcli failed; NetworkManager and Wi-Fi must be running");
 std::size_t pos=0;while(pos<out.size()){
  auto end=out.find('\n',pos);if(end==std::string::npos)end=out.size();std::string line=out.substr(pos,end-pos);pos=end+1;
  if(line.empty()||line[0]!='*')continue;
  auto last=line.rfind(':');if(last==std::string::npos)continue;
  auto previous=line.rfind(':',last-1);if(previous==std::string::npos)continue;
  std::string name=line.substr(2,previous-2);
  int signal=0;try{signal=std::stoi(line.substr(previous+1,last-previous-1));}catch(...){continue;}
  if(signal<1||signal>100)continue;
  return {unix_time_ms(),signal,interface_name_,name,-1};
 }
 throw std::runtime_error("No connected Wi-Fi network signal found. Connect to an access point and retry.");
}
}
