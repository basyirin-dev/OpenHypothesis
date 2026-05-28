"""OpenHypothesis — a transparent, open-source framework for AI-driven scientific discovery.

Usage::

    from openhypothesis import Discover

    result = await Discover(question="Is P = NP?").execute()
"""

from openhypothesis._discover import Discover

__all__ = ["Discover"]
