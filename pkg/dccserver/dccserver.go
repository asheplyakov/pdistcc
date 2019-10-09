package server

import (
	"bytes"
	"fmt"
	"github.com/asheplyakov/pdistcc/pkg/dccproto"
	"github.com/golang/glog"
	"io"
	"log"
)

type DccServer struct {
	version int
	rsock   io.Reader
	wsock   io.Writer
}

func NewDccServer() (s *DccServer, err error) {
	s = new(DccServer)
	s.version = 1
	return
}

func (s *DccServer) readCompilerArgs() (cmd []string, err error) {
	var argc int
	argc, err = dccproto.ReadToken(s.rsock, "ARGC")
	if err != nil {
		glog.Errorf("failed to read ARGC: %v", err)
		return
	}
	if argc <= 0 {
		err = fmt.Errorf("Negative ARGC")
		glog.Errorf("negative argc: %d", argc)
		return
	}
	for i := 0; i < argc; i++ {
		var buf bytes.Buffer
		if err = dccproto.ReadTokenTo(s.rsock, "ARGV", &buf); err != nil {
			glog.Errorf("failed to read %dth argument", i)
			return
		}
		cmd = append(cmd, buf.String())
	}
	return
}

func (s *DccServer) readRequest(doti io.Writer) (cmd []string, err error) {
	var (
		version int
	)
	version, err = dccproto.ReadToken(s.rsock, "DIST")
	if err != nil {
		log.Println("DccServer.readRequest: no valid greeting")
		return
	}
	if version != s.version {
		err = fmt.Errorf("unsupported version of DISTCC protocol %d", version)
		glog.Errorln(err)
		return
	}
	if cmd, err = s.readCompilerArgs(); err != nil {
		glog.Errorf("failed to read compiler args: %v", err)
		return
	}
	return
}
