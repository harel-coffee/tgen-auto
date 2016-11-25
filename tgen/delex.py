#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Delexicalization functions.
"""
from __future__ import unicode_literals

from tgen.data import DA, DAI, Abst


def find_substr(needle, haystack):
    """Find a sub-list in a list of tokens.

    @param haystack: the longer list of tokens – the list where we should search
    @param needle: the shorter list – the list whose position is to be found
    @return: a tuple of starting and ending position of needle in the haystack, \
            or None if not found
    """
    h = 0
    n = 0
    while True:
        if n >= len(needle):
            return h - n, h
        if h >= len(haystack):
            return None
        if haystack[h] == needle[n]:
            n += 1
            h += 1
        else:
            if n > 0:
                n = 0
            else:
                h += 1


def find_substr_approx(needle, haystack):
    """Try to find a sub-list in a list of tokens using fuzzy matching (skipping some
    common prepositions and punctuation, checking for similar-length substrings)"""
    # some common 'meaningless words'
    stops = set(['and', 'or', 'in', 'of', 'the', 'to', ',', 'restaurant'])
    h = 0
    n = 0
    match_start = 0
    while True:
        n_orig = n  # remember that we skipped some stop words at beginning of needle
                    # (since we check needle position before moving on in haystack)
        # skip stop words (ignore stop words around haystack position)
        while n < len(needle) and needle[n] in stops:
            n += 1
        while n > 0 and n < len(needle) and h < len(haystack) and haystack[h] in stops:
            h += 1
        if n >= len(needle):
            return match_start, h
        if h >= len(haystack):
            return None
        # fuzzy match: one may be substring of the other, with up to 2 chars difference
        # (moderate/moderately etc.)
        if (haystack[h] == needle[n] or
            (haystack[h] != '' and
             (haystack[h] in needle[n] or needle[n] in haystack[h]) and
             abs(len(haystack[h]) - len(needle[n])) <= 2)):
            n += 1
            h += 1
        else:
            if n_orig > 0:
                n = 0
            else:
                h += 1
                match_start = h


def delex_sent(da, conc, abst_slots, slot_names):
    """Abstract the given slots in the given sentence (replace them with X).

    @param da: concrete DA
    @param conc: concrete sentence text (string -- split only on whitespace, or list of tokens)
    @param abst_slots: a set of slots to be abstracted
    @param slot_names: boolean -- use slot names in the abstraction (X-slot), or just X?
    @return: a tuple of the abstracted text (in the same format as conc), abstracted DA, \
        and abstraction instructions
    """
    return_string = False
    if isinstance(conc, basestring):
        toks = conc.split(' ')
        return_string = True
    else:
        toks = conc
    absts = []
    abst_da = DA()
    toks_mask = [True] * len(toks)

    # find all values in the sentence, building the abstracted DA along the way
    # search first for longer values (so that substrings don't block them)
    for dai in sorted(da,
                      key=lambda dai: len(dai.value) if dai.value is not None else 0,
                      reverse=True):
        # first, create the 'abstracted' DAI as the copy of the current DAI
        abst_da.append(DAI(dai.da_type, dai.slot, dai.value))
        if dai.value is None:
            continue
        # try to find the value in the sentence (first exact, then fuzzy)
        # while masking tokens of previously found values
        val_toks = dai.value.split(' ')
        pos = find_substr(val_toks, [t if m else '' for t, m in zip(toks, toks_mask)])
        if pos is None:
            pos = find_substr_approx(val_toks, [t if m else '' for t, m in zip(toks, toks_mask)])
        if pos is not None:
            for idx in xrange(pos[0], pos[1]):  # mask found things so they're not found twice
                toks_mask[idx] = False
        if pos is None or pos == (0, 0):  # default to -1 for unknown positions
            pos = -1, -1
        # if the value is to be abstracted, replace the value in the abstracted DAI
        # and save abstraction instruction (even if not found in the sentence)
        if dai.slot in abst_slots and dai.value != 'dont_care':
            abst_da[-1].value = 'X-' + dai.slot
            # save the abstraction instruction
            absts.append(Abst(dai.slot, dai.value, start=pos[0], end=pos[1]))

    # go from the beginning of the sentence, replacing the values to be abstracted
    absts.sort(key=lambda a: a.start)
    shift = 0
    for abst in absts:
        # select only those that should actually be abstracted on the output
        if abst.slot not in abst_slots or abst.value == 'dont_care' or abst.start < 0:
            continue
        # replace the text
        if slot_names:
            toks[abst.start - shift:abst.end - shift] = ['X-' + abst.slot]
        else:
            toks[abst.start - shift:abst.end - shift] = ['X']
        # update abstraction instruction indexes
        shift_add = abst.end - abst.start - 1
        abst.start -= shift
        abst.end = abst.start + 1
        shift += shift_add

    return ' '.join(toks) if return_string else toks, abst_da, absts

