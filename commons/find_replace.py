def find_replace(path, regexp, substitution, append_fallback=False):
    import fileinput, io, os

    found = False

    if os.path.isfile(path):
        for line in fileinput.input(path, inplace=True):
            if re.match(regexp, line):
                found = True
                print(substitution)
            else:
                print(line)

    if not found and append_fallback:
        with io.open(self.loader_conf, 'ab') as f:
            f.write(substitution)
