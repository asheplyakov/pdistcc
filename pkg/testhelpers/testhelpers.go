package testhelpers

import (
	"errors"
)

type FaultyWriter int

func (w *FaultyWriter) Write(p []byte) (n int, err error) {
	return 0, errors.New("you should not pass")
}

type FaultyReader int

func (r *FaultyReader) Read(p []byte) (n int, err error) {
	return 0, errors.New("you should not pass")
}

type LimitedWriter struct {
	Capacity  int
	remaining int
}

func NewLimitedWriter(capacity int) *LimitedWriter {
	w := new(LimitedWriter)
	w.Capacity = capacity
	w.remaining = capacity
	return w
}

func (w *LimitedWriter) Write(p []byte) (n int, err error) {
	if w.remaining <= 0 {
		err = errors.New("out of buffer space")
	} else if w.remaining < len(p) {
		n = w.remaining
	} else {
		n = len(p)
	}
	w.remaining -= n
	return
}

type ShortReader int

func (r *ShortReader) Read(p []byte) (n int, err error) {
	if len(p) >= 1 {
		p[0] = 'a'
		n = 1
	}
	return
}
