#!/usr/bin/python2
"""Maths utils."""

def symmod(x1, x2):
    """Return x1 % x2, but with output values between -x2/2 and x2/2."""
    return ((x1 + x2/2.) % x2) - x2/2.
