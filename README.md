
<!-- README.md is generated from README.Rmd. Please edit that file -->
Learning statistics with R
==========================

This repository contains all the source materials for *Learning Statistics with R*. There are three versions of the content, the `original` version (LSR v0.6) written in LaTeX, the `bookdown` adaptation (LSR v0.6.1), and the new `pretext` version. The versions are kept in distinct folders to ensure they share no dependencies.

PreTeXt
-------

A PreTeXt version of the book is now available in the `pretext` directory. This version includes support for R code examples with syntax highlighting and image support. The PreTeXt version is automatically built and deployed to GitHub Pages via GitHub Actions. See `pretext/README.md` for more details on building and working with the PreTeXt version.

Bookdown
--------

To generate the bookdown version, source the `bookdown/serve_book.R` script. The generated book appears in the `bookdown/_book` subdirectory.

Original
--------

To typeset the original LaTeX version, the root file is `original/pdf/lsr.tex`, and the generated file is the `original/pdf/lsr.pdf` file it produces.

Docs
----

GitHub pages deploys the site from the `docs` directory; to publish an updated version of the bookdown version to <https://learningstatisticswithr.com> just copy the entire contents of `bookdown/_book` to `docs/book`, and push to GitHub.
