"""
UddoktaPay payment gateway client.

Wraps the Create Charge (checkout-v2) and Verify Payment APIs
provided by UddoktaPay.
"""

import logging
from dataclasses import dataclass

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

CHECKOUT_PATH = '/api/checkout-v2'
VERIFY_PATH = '/api/verify-payment'
REQUEST_TIMEOUT = 30  # seconds


class UddoktaPayError(Exception):
    """Raised when UddoktaPay returns an error or the request fails."""


@dataclass
class CheckoutResult:
    """Successful response from the Create Charge API."""

    status: bool
    message: str
    payment_url: str


@dataclass
class VerifyResult:
    """Successful response from the Verify Payment API."""

    full_name: str
    email: str
    amount: str
    fee: str
    charged_amount: str
    invoice_id: str
    metadata: dict
    payment_method: str
    sender_number: str
    transaction_id: str
    date: str
    status: str


def _headers() -> dict[str, str]:
    return {
        'RT-UDDOKTAPAY-API-KEY': settings.UDDOKTAPAY_API_KEY,
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'LabLink/1.0',
    }


def _base_url() -> str:
    return settings.UDDOKTAPAY_BASE_URL.rstrip('/')


def create_charge(
    *,
    full_name: str,
    email: str,
    amount: str,
    redirect_url: str,
    cancel_url: str | None = None,
    webhook_url: str | None = None,
    metadata: dict | None = None,
    return_type: str = 'GET',
) -> CheckoutResult:
    """
    Create a payment charge via UddoktaPay checkout-v2 API.

    Returns a ``CheckoutResult`` containing the ``payment_url``
    that the customer should be redirected to.
    """
    url = f'{_base_url()}{CHECKOUT_PATH}'
    payload: dict = {
        'full_name': full_name,
        'email': email,
        'amount': str(amount),
        'redirect_url': redirect_url,
        'return_type': return_type,
        'cancel_url': cancel_url or redirect_url,
        'webhook_url': webhook_url or '',
        'metadata': metadata or {},
    }

    logger.info('UddoktaPay create_charge → %s', url)

    try:
        resp = requests.post(
            url, json=payload, headers=_headers(), timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.exception('UddoktaPay create_charge failed')
        raise UddoktaPayError(f'Network error: {exc}') from exc

    data = resp.json()
    if not data.get('status'):
        msg = data.get('message', 'Unknown error')
        raise UddoktaPayError(f'UddoktaPay error: {msg}')

    return CheckoutResult(
        status=data['status'],
        message=data.get('message', ''),
        payment_url=data['payment_url'],
    )


def verify_payment(*, invoice_id: str) -> VerifyResult:
    """
    Verify the status of a payment by its ``invoice_id``.

    Returns a ``VerifyResult`` with all payment details.
    """
    url = f'{_base_url()}{VERIFY_PATH}'
    payload = {'invoice_id': invoice_id}

    logger.info('UddoktaPay verify_payment → %s (invoice=%s)', url, invoice_id)

    try:
        resp = requests.post(
            url, json=payload, headers=_headers(), timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.exception('UddoktaPay verify_payment failed')
        raise UddoktaPayError(f'Network error: {exc}') from exc

    data = resp.json()

    # Error responses have a "message" key and no "status" field
    if 'status' not in data:
        msg = data.get('message', 'Unknown error')
        raise UddoktaPayError(f'UddoktaPay error: {msg}')

    return VerifyResult(
        full_name=data.get('full_name', ''),
        email=data.get('email', ''),
        amount=data.get('amount', ''),
        fee=data.get('fee', ''),
        charged_amount=data.get('charged_amount', ''),
        invoice_id=data.get('invoice_id', ''),
        metadata=data.get('metadata', {}),
        payment_method=data.get('payment_method', ''),
        sender_number=data.get('sender_number', ''),
        transaction_id=data.get('transaction_id', ''),
        date=data.get('date', ''),
        status=data['status'],
    )
