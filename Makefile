publish:
	rm -rf dist
	flit build
	flit publish --repository teletraan
