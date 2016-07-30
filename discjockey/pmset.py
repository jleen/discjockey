# Based upon https://github.com/pudquick/pypmset/blob/master/pypmset.py
# Released under the MIT License

from ctypes import c_uint32, cdll, c_void_p, POINTER, byref
from CoreFoundation import CFStringCreateWithCString, kCFStringEncodingASCII
import objc

libIOKit = cdll.LoadLibrary('/System/Library/Frameworks/IOKit.framework/IOKit')
libIOKit.IOPMAssertionCreateWithName.argtypes = [c_void_p, c_uint32, c_void_p,
                                                 POINTER(c_uint32)]
libIOKit.IOPMAssertionRelease.argtypes = [c_uint32]


def cfstr(py_string):
    return CFStringCreateWithCString(None, py_string, kCFStringEncodingASCII)


def raw_ptr(pyobjc_string):
    return objc.pyobjc_id(pyobjc_string.nsstring())


def create_assertion_with_name(assert_name, assert_level, assert_msg):
    assert_id = c_uint32(0)
    p_assert_name = raw_ptr(cfstr(assert_name))
    p_assert_msg = raw_ptr(cfstr(assert_msg))
    errcode = libIOKit.IOPMAssertionCreateWithName(p_assert_name,
                                                   assert_level, p_assert_msg,
                                                   byref(assert_id))
    return errcode, assert_id


IOPMAssertionRelease = libIOKit.IOPMAssertionRelease

kIOPMAssertionTypeNoIdleSleep = b"NoIdleSleepAssertion"
kIOPMAssertionLevelOn = 255


# Stop idle sleep
def prevent_idle_sleep(reason):
    # TODO(jleen): The "reason" string doesn't seem to get used.  Why?
    errcode, assert_id = create_assertion_with_name(
            kIOPMAssertionTypeNoIdleSleep, kIOPMAssertionLevelOn,
            reason.encode('ascii'))
    if errcode != 0:
        raise Exception()
    return assert_id


# prove it to yourself with this on the Terminal: pmset -g assertions

# Let it go again
def allow_idle_sleep(assert_id):
    errcode = IOPMAssertionRelease(assert_id)
    if errcode != 0:
        raise Exception()
