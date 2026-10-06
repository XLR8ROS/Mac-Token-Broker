class TokenBrokerError(Exception):
    """Base error for broker failures."""


class BrokerUnavailable(TokenBrokerError):
    pass


class UnknownService(TokenBrokerError):
    pass


class CredentialNotAssigned(TokenBrokerError):
    pass


class CredentialMissing(TokenBrokerError):
    pass


class CredentialInvalid(TokenBrokerError):
    pass


class ProviderRejectedCredential(TokenBrokerError):
    pass


class CredentialRefreshFailed(TokenBrokerError):
    pass


class BrokerStorageFailure(TokenBrokerError):
    pass


class MalformedRequest(TokenBrokerError):
    pass
