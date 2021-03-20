class SISError(Exception):
    def __init__(self, code, desc):
        super().__init__(desc)
        self.code = code


class InvalidInputNumberError(SISError):
    def __init__(self):
        super().__init__(1, "Invalid input number")


class InvalidSwitchAttemptError(SISError):
    def __init__(self):
        super().__init__(6, "Invalid switch attempt in this mode")


class InvalidFunctionNumberError(SISError):
    def __init__(self):
        super().__init__(9, "Invalid function number")


class InvalidCommandError(SISError):
    def __init__(self):
        super().__init__(10, "Invalid command")


class InvalidPresetNumberError(SISError):
    def __init__(self):
        super().__init__(11, "Invalid preset number")


class InvalidPortNumberError(SISError):
    def __init__(self):
        super().__init__(12, "Invalid port number")


class InvalidParameterError(SISError):
    def __init__(self):
        super().__init__(13, "Invalid parameter")


class InvalidConfigurationError(SISError):
    def __init__(self):
        super().__init__(14, "Not valid for this configuration")


class InvalidCommandForSignalTypeError(SISError):
    def __init__(self):
        super().__init__(17, "Invalid command for signal type")


class BusyError(SISError):
    def __init__(self):
        super().__init__(22, "Busy")


class PrivilegeViolationError(SISError):
    def __init__(self):
        super().__init__(24, "Privilege violation")


class DeviceNotPresentError(SISError):
    def __init__(self):
        super().__init__(25, "Device not present")


class MaximumNumberOfConnectionsExceededError(SISError):
    def __init__(self):
        super().__init__(26, "Maximum number of connections exceeded")


class InvalidEventNumberError(SISError):
    def __init__(self):
        super().__init__(27, "Invalid event number")


class BadFileNameError(SISError):
    def __init__(self):
        super().__init__(28, "Bad filename/File not found")


# E30 is supposedly followed with "colon and a descriptor number"
class HardwareFailureError(SISError):
    def __init__(self):
        super().__init__(30, "Hardware failure")


class AttemptToBreakPortPassthroughError(SISError):
    def __init__(self):
        super().__init__(31, "Attempt to break port passthrough when not set")


class IncorrectVChipPasswordError(SISError):
    def __init__(self):
        super().__init__(32, "Incorrect V-chip password")


class BadFileTypeForLogoError(SISError):
    def __init__(self):
        super().__init__(33, "Bad file type for logo")


# Create an exception class mapping for each error code.
_codes_to_exception_classes = {}

for _exc_cls in [
    InvalidInputNumberError,
    InvalidSwitchAttemptError,
    InvalidFunctionNumberError,
    InvalidCommandError,
    InvalidPresetNumberError,
    InvalidPortNumberError,
    InvalidParameterError,
    InvalidConfigurationError,
    InvalidCommandForSignalTypeError,
    BusyError,
    PrivilegeViolationError,
    DeviceNotPresentError,
    MaximumNumberOfConnectionsExceededError,
    InvalidEventNumberError,
    BadFileNameError,
    HardwareFailureError,
    AttemptToBreakPortPassthroughError,
    IncorrectVChipPasswordError,
    BadFileTypeForLogoError,
]:
    exc_cls_obj = _exc_cls()
    _codes_to_exception_classes["E{0}".format(exc_cls_obj.code)] = _exc_cls


def exception_from_error_code(code: str) -> SISError:
    """Return an exception object for this error code.

    Args:
        code (str): an error string, such as "E13"
    """
    if code in _codes_to_exception_classes:
        return _codes_to_exception_classes[code]()
    else:
        return SISError(code, "")
