
import pytest
import subprocess

from pytest_mock import mocker
from unittest.mock import MagicMock

from ..compiler.wrapper import CompilerWrapper
from ..compiler.errors import PreprocessorFailed

import pdistcc


def test_wrapper(mocker):
    mocker.patch('subprocess.check_output')
    mocker.patch('pdistcc.compiler.wrapper.dcc_compile')
    wrapper = CompilerWrapper('gcc -c -o foo.o foo.c'.split())
    setattr(wrapper, 'can_handle_command', MagicMock())
    wrapper.can_handle_command.return_value = None
    setattr(wrapper, 'preprocessor_cmd', MagicMock())
    wrapper.preprocessor_cmd.return_value = 'gcc -E -o foo.i foo.c'.split()
    setattr(wrapper, 'compiler_cmd', MagicMock())
    wrapper.compiler_cmd.return_value = 'gcc -c -o foo.o -x c foo.i'.split()
    setattr(wrapper, 'object_file', MagicMock())
    wrapper.object_file.return_value = 'foo.o'
    setattr(wrapper, 'preprocessed_file', MagicMock())
    wrapper.preprocessed_file.return_value = 'foo.i'
    host = '127.0.0.1'
    port = '3632'
    wrapper.wrap_compiler(host, port)
    pdistcc.compiler.wrapper.dcc_compile.assert_called_once_with(
        'foo.i',
        'gcc -c -o foo.o -x c foo.i'.split(),
        host=host,
        port=port,
        ofile='foo.o'
    )
    subprocess.check_output.assert_called_once_with(
        'gcc -E -o foo.i foo.c'.split()
    )


def test_wrapper_preprocessor_failed(mocker):
    mocker.patch('subprocess.check_output')
    subprocess.check_output.side_effect = subprocess.CalledProcessError(1, 'XX')
    mocker.patch('pdistcc.compiler.wrapper.dcc_compile')
    wrapper = CompilerWrapper('gcc -c -o foo.o foo.c'.split())
    setattr(wrapper, 'can_handle_command', MagicMock())
    wrapper.can_handle_command.return_value = None
    setattr(wrapper, 'preprocessor_cmd', MagicMock())
    wrapper.preprocessor_cmd.return_value = 'gcc -E -o foo.i foo.c'.split()
    setattr(wrapper, 'compiler_cmd', MagicMock())
    setattr(wrapper, 'object_file', MagicMock())
    setattr(wrapper, 'preprocessed_file', MagicMock())
    host = '127.0.0.1'
    port = '3632'
    with pytest.raises(PreprocessorFailed):
        wrapper.wrap_compiler(host, port)

    subprocess.check_output.assert_called_once_with(
        'gcc -E -o foo.i foo.c'.split()
    )
    pdistcc.compiler.wrapper.dcc_compile.assert_not_called()
    wrapper.compiler_cmd.assert_not_called()
    wrapper.object_file.assert_not_called()
