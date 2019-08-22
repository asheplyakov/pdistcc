
all: thunderingherd

.o/thunderingherd.o: dat/thunderingherd.cpp
	@mkdir -p "$(dir $@)"
	./bin/pdistcc.py $(CXX) -std=c++11 -Wall -pthread -O2 -g -c -o $@ $<

thunderingherd: .o/thunderingherd.o
	$(CXX) -pthread -o $@ $^

clean:
	@rm -f .o/thunderingherd.o
	@rm -f .o/thunderingherd.ii
	@rm -f thunderingherd
