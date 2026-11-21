#pragma once
#include "wifisense/signal_sample.hpp"
#include <string>
namespace wifisense { class CsvWriter { public: explicit CsvWriter(const std::string&); ~CsvWriter(); CsvWriter(const CsvWriter&) = delete; CsvWriter& operator=(const CsvWriter&) = delete; void write(const SignalSample&); bool good() const; private: class Impl; Impl* impl_; }; }
