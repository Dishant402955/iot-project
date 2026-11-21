#include "wifisense/csv_writer.hpp"
#include <fstream>
#include <stdexcept>
namespace wifisense {
class CsvWriter::Impl{public:explicit Impl(const std::string&p):out(p,std::ios::app){if(!out)throw std::runtime_error("Cannot open CSV output: "+p);if(out.tellp()==0)out<<"timestamp_ms,interface,network_name,signal_percent,label\n";}std::ofstream out;};
CsvWriter::CsvWriter(const std::string&p):impl_(new Impl(p)){}
CsvWriter::~CsvWriter(){delete impl_;}
void CsvWriter::write(const SignalSample&s){impl_->out<<s.timestamp_ms<<','<<s.interface_name<<','<<s.network_name<<','<<s.signal_percent<<','<<s.label<<'\n';impl_->out.flush();}
bool CsvWriter::good()const{return impl_&&bool(impl_->out);}
}
