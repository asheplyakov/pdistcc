package dccclient

import (
	"fmt"
	"github.com/asheplyakov/pdistcc/pkg/dccproto"
	"io"
	"log"
	"net"
	"os"
)

type DccClient struct {
	version int
	rsock   io.Reader
	wsock   io.Writer
	stdout  io.Writer
	stderr  io.Writer
	doti    io.Reader
	dotilen int
	ofile   io.Writer
}

func (c *DccClient) Request(args []string) (err error) {
	var sz int64
	err = dccproto.SendToken(c.wsock, "DIST", c.version)
	if err != nil {
		return
	}
	err = dccproto.SendToken(c.wsock, "ARGC", len(args))
	if err != nil {
		return
	}
	for i, arg := range args {
		err = dccproto.SendStringToken(c.wsock, "ARGV", arg)
		if err != nil {
			log.Println("Failed to send arg", i)
			return
		}
	}
	err = dccproto.SendToken(c.wsock, "DOTI", c.dotilen)
	if err != nil {
		return
	}
	sz, err = io.Copy(c.wsock, c.doti)
	if err != nil {
		if sz != int64(c.dotilen) {
			log.Printf("Failed to send DOTI file: partial write: %d bytes of %d", int(sz), c.dotilen)
		} else {
			log.Println("Failed to send DOTI file:", err)
		}
		return
	}
	return
}

func (c *DccClient) HandleResponse() (status int, err error) {
	var (
		version int
	)
	if version, err = dccproto.ReadToken(c.rsock, "DONE"); err != nil {
		err = fmt.Errorf("haven't got a valid distcc greeting: %v", err)
		return
	}
	if version != c.version {
		err = fmt.Errorf("Unsupported protocol version: %d", version)
		return
	}
	if status, err = dccproto.ReadToken(c.rsock, "STAT"); err != nil {
		err = fmt.Errorf("haven't got a valid STAT: %v", err)
		return
	}
	if err = dccproto.ReadTokenTo(c.rsock, "SERR", c.stderr); err != nil {
		return
	}
	if err = dccproto.ReadTokenTo(c.rsock, "SOUT", c.stdout); err != nil {
		return
	}
	if status == 0 {
		if err = dccproto.ReadTokenTo(c.rsock, "DOTO", c.ofile); err != nil {
			log.Println("failed to receive object file")
		}
	}
	return
}

func (c *DccClient) Compile(args []string) (status int, err error) {
	status = -1
	if err = c.Request(args); err != nil {
		log.Println("failed to enqueue compilation", err)
		return
	}
	status, err = c.HandleResponse()
	if err != nil {
		log.Println("failed to process server response", err)
	}
	return
}

func DccCompile(args []string, src string, obj string, where string) (status int, err error) {
	status = -1
	var (
		c       DccClient
		conn    net.Conn
		inf     os.FileInfo
		doti    *os.File
		objfile *os.File
	)

	c.version = 1
	c.stdout = os.Stdout
	c.stderr = os.Stderr

	if doti, err = os.Open(src); err != nil {
		log.Println("failed to open preprocessed source file", src)
		return
	}
	defer doti.Close()
	if inf, err = doti.Stat(); err != nil {
		log.Println("failed to stat preprocessed source file", src)
		return
	}
	c.dotilen = int(inf.Size())
	c.doti = doti

	if objfile, err = os.Create(obj); err != nil {
		log.Println("failed to open object file", obj, "for writing")
		return
	}
	defer objfile.Close()
	c.ofile = objfile

	if conn, err = net.Dial("tcp", where); err != nil {
		log.Println("failed to connect to", where)
		return
	}
	defer conn.Close()
	c.rsock = conn
	c.wsock = conn

	status, err = c.Compile(args)
	return
}
