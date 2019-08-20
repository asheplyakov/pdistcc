
all: thunderingherd dat/thunderingherd.ii thunderingherd.o


dat/thunderingherd.ii: dat/thunderingherd.cpp
	$(CXX) -std=c++11 -pthread -E -o $@ $<

thunderingherd.o: dat/thunderingherd.ii
	python3 ./pdistcc/pdistcc.py "$<" "$@" -- /usr/bin/g++ -std=c++11 -pthread -O2 -g -c dat/thunderingherd.cpp

thunderingherd: thunderingherd.o
	/usr/bin/g++ -pthread -o $@ $^

clean:
	@rm -f thunderingherd.o
	@rm -f thunderingherd
