package wrappers

type UnsupportedCompilationMode struct {
	Msg string
}

func (e *UnsupportedCompilationMode) Error() string {
	return e.Msg
}
