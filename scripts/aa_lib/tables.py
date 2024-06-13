#!/usr/bin/python
"""String table utilities.

    Author
    ------
    Andreas Anhaeuser
    Insitute for Geophysics and Meteorology
    University of Cologne
    Germany
    <andreas.anhaeuser@uni-koeln.de>
    <andreas.anhaeuser@posteo.net> (after expiry the above)
"""

# standard modules
import os
from collections.abc import Iterable
from copy import deepcopy as copy

# PyPI modules
import numpy as np

_str_delims = ('"', "'")

def read_vartable(filename, sep='|', comment='#', ignore_str=' '):
    """Read variable table text file and return as a dict.

        The first non-comment line is the header line. The returned dict
        consists of lists. The header line of the text file defines number and
        names of the dict keys. The subsequent lines are the entries of the
        dict, with each column grouped to its respective header.

        Parameters
        ----------
        filename : str
            location of the variable table file
        sep : str, optional
            column separator. Default: '|'
        comment : str, optional
            comment string. Set to '' or None to deactivate. Default: '#'
        ignore_str : str, optional
            The entries are shortened while they start or end on this string.
            Set to '' or None to deactivate. Default: ' '

        Returns
        -------
        table : dict
            keys are the header

        Example
        -------
        A table file that looks as shown below produces this output:
        
        {'py_name' : ['varname1', 'varname2', 'varname3'],
         'nc_name' : ['ncvn1', 'ncvn2', 'ncvn3'],
         'gain' : ['1', '1000', '1'],
         'offset' : ['0', '', '200']
         }

        py_name     | nc_name | gain | offset 
        ------------+---------+------+--------
        varname1    | ncvn1   |    1 |      0 
        varname2    | ncvn2   | 1000 |        
        varname3    | ncvn3   |    1 |    200 


        History
        ------
        Written in 2016
    """
    if not os.path.isfile(filename):
        raise IOError('Cannot access file ' + filename)

    ###################################################
    # READ FILE                                       #
    ###################################################
    fid = open(filename, 'r')
    lines = fid.readlines()
    fid.close()

    ###################################################
    # INITIALIZE                                      #
    ###################################################
    init = False
    headers = []
    table   = {}
    S = len(sep)
    if any(ignore_str):
        I = len(ignore_str)
    else:
        I = 0
    if any(comment):
        C = len(comment)
    else:
        C = 0

    ###################################################
    # LOOP OVER LINES                                 #
    ###################################################
    for line in lines:
        ###################################################
        # SPLIT LINE INTO WORDS                           #
        ###################################################
        # the last word is removed because it is just the new line character:
        words = line.split(sep)[:-1]
        Nwords = len(words)

        # delete leading and trailing white spaces:
        for n in range(Nwords):
            word = words[n]
            while I > 0 and len(word) > 0 and word[:I]  == ignore_str:
                word = word[I:]
            while I > 0 and len(word) > 0 and word[-I:] == ignore_str:
                word = word[:-I]
            words[n] = word

        ###################################################
        # EMPTY LINE                                      #
        ###################################################
        if not any(words):
            continue

        ###################################################
        # COMMENT LINE                                    #
        ###################################################
        if C > 0 and any(words[0]) and words[0][:C] == comment:
            continue

        ###################################################
        # HEADER LINE                                     #
        ###################################################
        if not init:
            for word in words:
                table[word] = []
                headers.append(word)
            Ncols = len(headers)
            init  = True
            continue
        
        ###################################################
        # NON-DATA LINE                                   #
        ###################################################
        if len(words) != Ncols: 
            continue
        
        ###################################################
        # DATA LINE                                       #
        ###################################################
        for n in range(Ncols):
            word   = words[n]
            header = headers[n]
            table[header].append(word)

    return table

def read_namelist(filename, *args, **kwargs):
    """Read namelist (setup) text file and return as a dict.

        Parameters
        ----------
        filename : str
            location of the variable table file
        name_end : str, optional
            string that marks the end of the parameter name. Default: ':'
        sep : str, optional
            string that separates elements of a value list. Default: ','
        comment : str, optional
            string that indicates the start of a comment. Default: '#'
        ignore_char : str, optional
            The entries are shortened while they start or end on this
            character(s).  Set to '' to deactivate. Default: ' '
        convert_to_number : bool, optional
            If True, entries that are not bounded by ' or " are converted to
            number (int or float). Default: False
        conversion_error : bool, optional
            If True, an error is thrown on attempted number conversion on
            invalid string. Default: False

        Returns
        -------
        table : dict
            keys are the header
        
        Example
        -------
        An ascii file like this
        
        name : Berlin
        population : 3466164
        districts : Wedding, Marzahn, Pankow        # ... and some more
        area code : 030
        # coolest clubs : outdated information
        average temperature : 9.7
        
        is returned as this dictionary:
        
        >>> namelist
        {'name' : 'Berlin',
        'population' : '3466164',
        'districts' : ['Wedding', 'Marzahn', 'Pankow'],
        'area code' : '030',
        'average temperature' : '9.7',
        }

        History
        -------
        Written in 2016-2019
    """
    if not os.path.isfile(filename):
        raise IOError('Cannot access file ' + filename)

    ###################################################
    # READ FILE                                       #
    ###################################################
    with open(filename, 'r') as fid:
        lines = fid.readlines()

    return get_namelist(lines, *args, **kwargs)

def read_structured_namelist(filename, *args, **kwargs):
    """Read structured namelist (setup) text file and return as a dict."""
    if not os.path.isfile(filename):
        raise IOError('Cannot access file ' + filename)

    ###################################################
    # READ FILE                                       #
    ###################################################
    with open(filename, 'r') as fid:
        lines = fid.readlines()

    return get_structured_namelist(lines, *args, **kwargs)

def get_structured_namelist(lines, struc_sep='>', *args, **kwargs):
    """Return a dict of dict."""
    N = len(lines)
    found = False
    for n, line in enumerate(lines):
        if line.strip()[:1] == struc_sep:
            nbeg = n
            found = True
            break
    if not found:
        raise IOError('Cannot find structure separator %s' % struc_sep)

    namelist = {}

    while nbeg < N - 1:
        for n in range(nbeg+1, N):
            line = lines[n].strip()
            if line[:1] == struc_sep:
                nend = n
                break

            if n == N - 1:
                nend = n
                break

        key = lines[nbeg][1:].strip()
        if key in namelist.keys():
            raise IndexError('Duplicate key: %s' % key)

        namelist[key] = get_namelist(lines[nbeg+1:nend], *args, **kwargs)
        nbeg = nend

    return namelist

def get_namelist(
        lines, name_end=':', sep=',', comment='#', ignore_char=' ',
        convert_to_number=False, conversion_error=False,
        str_delims=_str_delims, strip_string_delimiters=True):
    """Convert list of lines to dict.

        Parameters
        ----------
        lines : list of str
        name_end : str, optional
            string that marks the end of the parameter name. Default: ':'
        sep : str, optional
            string that separates elements of a value list. Default: ','
        comment : str, optional
            string that indicates the start of a comment. Default: '#'
        ignore_char : str, optional
            The entries are shortened while they start or end on this
            character(s).  Set to '' to deactivate. Default: ' '
        convert_to_number : bool, optional
            If True, entries that are not bounded by ' or " are converted to
            number (int or float). Default: False
        conversion_error : bool, optional
            If True, an error is thrown on attempted number conversion on
            invalid string. Default: False

        Returns
        -------
        table : dict
            keys are the header

        Known bugs
        ----------
        String delimiters and lists
            Lists of elements that are surrounded by string delimiters (eg. ' )
            are not correctly parsed. For example:
                    parameter : 'value_1', 'value_2'
            is NOT parsed into {'parameter' : ['value_1', 'value_2']} You can
            get the correct behaviour by omitting the string delimiter ' if
            possible.
        

        Example
        -------
        An ascii file like this
        
        name : Berlin
        population : 3466164
        districts : Wedding, Marzahn, Pankow        # ... and some more
        area code : 030
        # coolest clubs : outdated information
        average temperature : 9.7
        
        is returned as this dictionary:
        
        >>> namelist
        {'name' : 'Berlin',
        'population' : '3466164',
        'districts' : ['Wedding', 'Marzahn', 'Pankow'],
        'area code' : '030',
        'average temperature' : '9.7',
        }
    """
    ###################################################
    # INITIALIZE                                      #
    ###################################################
    init = False
    namelist = {}

    E = len(name_end)
    S = len(sep)
    C = len(comment)

    ###################################################
    # LOOP OVER LINES                                 #
    ###################################################
    for line in lines:
        line = line.strip('\n')

        ###################################################
        # CUT OFF COMMENT                                 #
        ###################################################
        if C > 0 and comment in line:
            end = line.index(comment)
            line = line[:end]
        
        ###################################################
        # NON-DATA LINE                                   #
        ###################################################
        if not name_end in line:
            continue

        ###################################################
        # SPLIT LINE                                      #
        ###################################################
        i = line.index(name_end)
        name = line[:i]
        data = line[i+E:]

        name = name.strip(ignore_char)
        data = data.strip('\n').strip(ignore_char)

        ###################################################
        # SPLIT DATA                                      #
        ###################################################
        cond1 = S > 0
        cond2 = sep in data
        cond3 = not has_delimiters(data, str_delims)
        if cond1 and cond2 and cond3:
            data = data.split(sep)
            for n in range(len(data)):
                data[n] = data[n].strip(ignore_char)

        ###################################################
        # FLOAT CONVERSION                                #
        ###################################################
        if convert_to_number:
            try:
                data = str2num(data, str_delims)
            except ValueError as e:
                if conversion_error:
                    raise e
        
        ###################################################
        # REMOVE STRING DELIMITERS                        #
        ###################################################
        if strip_string_delimiters:
            if isinstance(data, str):
                data = strip_delimiters(data, str_delims)

        ###################################################
        # WRITE TO DICT                                   #
        ###################################################
        if name in namelist.keys():
            raise KeyError(name + ' appears multiple times in namelist.')
        namelist[name] = data
        
    return namelist

def has_delimiters(s, delims=_str_delims):
    """Return True if string starts and ends with the same string delimiter."""
    for delim in delims:
        if s[:1] == s[-1:] == delim:
            return True
    return False

def strip_delimiters(s, delims=_str_delims):
    for delim in delims:
        if s[:1] == s[-1:] == delim:
            return s[1:-1]
    return s

def str2num(s, str_delims=_str_delims):
    """Convert to number if it does not contain ' or " ."""
    # list case
    if not isinstance(s, str):
        if isinstance(s, Iterable):
            return [str2num(el) for el in s]

    # check whether s is bounded with ' or "
    str_delims = ('"', "'")
    if has_delimiters(s, str_delims):
        return s

    # try int
    if s.isdigit():
        number = int(s)

    # float
    else:
        number = float(s)

    return number

def column_list(
        headers, data, typ='s', align='l', column_width=16, precision=7,
        filename=None, comment_top=None, comment_bottom=None,
        ):
    """Write an ascii file with aligned columns.

        Parameters
        ----------
        headers : list of str, length N
            first line (will be commented)
        data : list of Iterable, length N
            The elements must be equal in length.
        typ : list of str, length N, optional
            {'s', 'f', 'e', 'i'} (i. e. str, float or exponential) Default: all
            str
        align : list of str, length N, optional
            {'l', 'c', 'r'} (i. e. left, center or right). Default: all left
        column_width : list of int, length N, optional
            Default: all 16
        precision : list of int, length N, optional
            number of digits after period. Default: all 7
        filename : str, optional
            path to file where the table is to be saved. Default: None

        Returns
        -------
        str

        History
        -------
        Written in 2016
    """
    ###################################################
    # INPUT CHECK                                     #
    ###################################################

    # ========== helper functions  ======================= #
    def expand(x, J):
        """Expand variable to length J if it is singleton."""
        if isinstance(x, Iterable):
            if len(x) == 1:
                return x * J
            elif len(x) == J:
                return x
            else:
                raise IndexError()
        else:
            return [x] * J

    def check_str(x):
        """Check whether variable is str or None. Raise error if not."""
        if x is None:
            return
        if isinstance(x, str):
            return
        raise TypeError()

    # ========== perform checks  ========================= #
    # headers
    assert isinstance(headers, Iterable)
    J = len(headers)

    # data
    assert isinstance(data, Iterable)
    assert len(data) == J
    init = False
    for x in data:
        assert isinstance(x, Iterable)
        if not init:
            N = len(x)
            init = True
        assert len(x) == N

    # length J variables
    typ = expand(typ, J)
    align = expand(align, J)
    column_width = expand(column_width, J)
    precision = expand(precision, J)

    # strings
    check_str(filename)
    check_str(comment_top)
    check_str(comment_bottom)

    ###################################################
    # ABBREVIATIONS                                   #
    ###################################################
    cw = column_width
    prec = precision

    ###################################################
    # INITIALIZE                                      #
    ###################################################
    text = ''

    ###################################################
    # WRITE HEADLINES                                 #
    ###################################################
    line = ''
    for j in range(J):
        if j == 0:
            word = '# ' + headers[j]
        else:
            word = headers[j]

        # justify
        if align[j] == 'l':
            word = word.ljust(cw[j])
        elif align[j] == 'c':
            word = word.center(cw[j])
        elif align[j] == 'r':
            word = word.rjust(cw[j])

        if j > 0:
            word = ' ' + word

        # append
        line = line + word
    text = text + line.rstrip()

    ###################################################
    # FORMATTERS                                      #
    ###################################################
    fmts = []
    for j in range(J):
        # justify
        if align[j] == 'l':
            a = '<'
        elif align[j] == 'c':
            a = '^'
        elif align[j] == 'r':
            a = '>'

        # ========== digits  ============================= #
        # float
        if typ[j] in 'ef':
            # e.g. ' {:12.4f}'
            d ='%1.0f.%1.0f' % (cw[j], prec[j]) + typ[j]
        # integer
        elif typ[j] == 'i':
            raise NotImplementedError('')
            # feel free to implement this
            d = '%1.0fd' % cw[j]
        # string
        elif typ[j] == 's':
            raise NotImplementedError('')
            # feel free to implement this
            d = '%1.0fs' % cw[j]
        else:
            raise NotImplementedError('')

        # formatter
        fmt = '{:' + a + d + '}'    # e.g. ' {:<14}'
        fmts.append(fmt)

    ###################################################
    # WRITE DATA                                      #
    ###################################################
    for n in range(N):
        line = '\n'
        for j in range(J):
            word = fmts[j].format(data[j][n])
            if j > 0:
                word = ' ' + word
            line = line + word
        text = text + line.rstrip()

    ###################################################
    # INCLUDE COMMENTS                                #
    ###################################################
    if comment_top is not None:
        lines = comment_top.split('\n')
        N = len(lines)
        for n in range(N):
            lines[n] = '# ' + lines[n] + '\n'
        text = ''.join(lines) + text

    if comment_bottom is not None:
        lines = comment_bottom.split('\n')
        N = len(lines)
        for n in range(N):
            lines[n] = '\n# ' + lines[n]
        text = text + ''.join(lines)

    # add final eol:
    text = text + '\n'

    ###################################################
    # WRITE TO FILE                                   #
    ###################################################
    if filename is not None:
        idx = filename.rfind('/')
        if idx >= 0:
            path = filename[:idx]
        else:
            path = '.'
        if not os.path.isdir(path):
            os.makedirs(path)
        if os.path.isfile(filename):
            os.remove(filename)
        with open(filename, 'w') as fid:
            fid.write(text)

    return text

def get_column_list(*args, **kwargs):
    """Alias to read_column_list."""
    return read_column_list(*args, **kwargs)

def read_column_list_with_headers(
        filename, sep=None, comment_str='#', convert_to_number=False,
        nan_str='nan', skip_invalid_rows=False):
    """Read text file structured in columns and return as dict.

        Parameters
        ----------
        filename : str
            path to text file
        sep : None or str, optional
            column separator, as in str.split(). Default: None
        comment_str : str, optional
            str indicating comments. Default: '#'
        convert_to_number : bool, optional
            column data are converted to numbers if this is possible for the
            whole column
        nan_str : str, optional
            This string is converted to nan where applicable. Only in effect if
            `convert_to_number` evaluates to True. Default: 'nan'

        Returns
        -------
        cols : dict
            keys are the header names

        Raises
        ------
        KeyError
            If a header appears multiple times
        IndexError
            If table contains less than two rows

        Caution
        -------
        Make sure the header row does not contain `comment_str`.
    """
    dtype = float

    cols = read_column_list(filename, sep=sep, comment_str=comment_str,
            skip_invalid_rows=skip_invalid_rows)

    data = {}
    for col in cols:
        rows = col
        if len(rows) < 2:
            raise IndexError('Table contains less than 2 rows.')

        header = rows[0]
        values = rows[1:]

        if convert_to_number:
            # `nan_str` --> 'nan'
            vals_tmp = copy(values)
            for nval, val in enumerate(vals_tmp):
                if val == nan_str:
                    vals_tmp[nval] = 'nan'

            # try to convert to floats
            try:
                values = np.array(vals_tmp, dtype=dtype)
            except ValueError as e:
                # not a purely numeric column
                pass

        data[header] = values

    return data

def read_column_list(filename, sep=None, skip_rows=0, comment_str='#',
        skip_invalid_rows=False):
    """Read text file structured in columns and return as list of lists.
    
        Parameters
        ----------
        filename : str
            path to text file
        sep : None or str, optional
            column separator, as in str.split(). Default: None
        skip_rows : int, optional
            number of rows at the beginning to skip, Detault: 0
        comment_str : str, optional
            str indicating comments. Default: '#'

        Returns
        -------
        cols : list of lists of str
            cols[i][j] contains the text of j-th row in the i-th column.
    """
    ###################################################
    # INPUT CHECK                                     #
    ###################################################
    assert isinstance(filename, str)
    assert os.path.isfile(filename)
    if sep is not None:
        assert isinstance(sep, str)
        assert len(sep) > 0
    assert isinstance(skip_rows, int)
    assert skip_rows >= 0

    if comment_str is None:
        comment_str = ''

    ###################################################
    # READ FILE                                       #
    ###################################################
    fid = open(filename)
    lines = fid.readlines()
    fid.close()

    ###################################################
    # RETRIEVE COLUMNS                                #
    ###################################################
    init = False
    for nline, line in enumerate(lines):
        # skip_rows
        if skip_rows > 0:
            skip_rows -= 1
            continue

        # remove leading and trailing white spaces and newline:
        line = line.strip('\n').strip()
        
        # skip empty line:
        if line == '':
            continue

        # comments
        if any(comment_str):
            i = line.find(comment_str)
            # skip comment line:
            if i == 0:
                continue
            # remove in-line comment:
            if i > 0:
                line = line[:i]

        words = line.split(sep)

        # initialize output arrays
        if not init:
            cols = [[] for word in words]
            N = len(words)
            init = True

        if len(words) != N:
            if skip_invalid_rows:
                continue
            else:
                raise Exception(
                        'Row contains %i columns, but should be %i.' 
                        % (len(words), N)
                        )

        for n in range(N):
            word = words[n].strip()
            cols[n].append(word)

    return cols

###################################################
# TESTS                                           #
###################################################
def get_column_list_with_headers___test_number_convertion():
    filename = 'tables__test_file_column_list.txt'
    sep = '|'
    convert_to_number = True

    data = read_column_list_with_headers(
            filename, sep=sep, convert_to_number=convert_to_number)

    for key in sorted(data):
        print('%s: %s' % (key.ljust(32), str(data[key])))


if __name__ == '__main__':
    get_column_list_with_headers___test_number_convertion()
