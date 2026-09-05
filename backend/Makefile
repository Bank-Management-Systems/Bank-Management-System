# ============================================================================
# Bank Management System - backend build
# Shared file: candidates normally do NOT need to edit the Makefile.
# Requires: g++ >= 9, libmysqlclient-dev, third_party/httplib.h (included)
# ============================================================================
CXX      ?= g++
CXXFLAGS := -std=c++17 -Wall -I. -Ithird_party
LDFLAGS  := -lmysqlclient -pthread
APP      := bank_server
HDRS     := common/http_utils.hpp common/db.hpp \
            candidate1_account/account_module.hpp \
            candidate2_transactions/transactions_module.hpp \
            candidate3_records/records_module.hpp \
            candidate4_security/security_module.hpp

all: $(APP)

$(APP): main.cpp $(HDRS) third_party/httplib.h
	$(CXX) $(CXXFLAGS) main.cpp -o $(APP) $(LDFLAGS)
	@echo "Build OK -> backend/$(APP)"

run: $(APP)
	./$(APP)

clean:
	rm -f $(APP)

.PHONY: all run clean
