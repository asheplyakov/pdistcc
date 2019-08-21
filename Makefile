
all: thunderingherd

.o/thunderingherd.o: dat/thunderingherd.cpp
	@mkdir -p "$(dir $@)"
	python3 ./pdistcc/pdistcc.py -- $(CXX) -std=c++11 -pthread -O2 -g -c -o $@ $<

thunderingherd: .o/thunderingherd.o
	$(CXX) -pthread -o $@ $^

clean:
	@rm -f .o/thunderingherd.o
	@rm -f thunderingherd
