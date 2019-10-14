package wrappers

import (
	"fmt"
	"github.com/asheplyakov/pdistcc/pkg/wrappers/gcc"
	"github.com/golang/glog"
)

type CompilerWrapper interface {
	MatchCompiler(args []string) bool
	CanHandleCommand(args []string) error
	PreprocessorCmd() ([]string, error)
	CompilerCmd() ([]string, error)
}

func Find(args []string) (obj CompilerWrapper, err error) {
	wrappers := []CompilerWrapper{&gcc.GccWrapper{}}
	for _, w := range wrappers {
		if w.MatchCompiler(args) {
			obj = w
			return
		}
	}
	err = fmt.Errorf(`No wrapper for "%v" can be found`, args)
	glog.Errorln(err)
	return
}
