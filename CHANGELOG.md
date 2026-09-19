# Changelog

All notable changes to Vetrina are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/).

## [1.2.0] - 2026-09-19

### Added
- The card shows the project's logo when the repository has one: the logo or icon its README
  shows, or else a picture named "logo" or "icon". Without one, or when the logo is an SVG or
  too long for the square, the owner's picture is used as before.

## [1.1.1] - 2026-09-19

### Fixed
- The downloaded apps could not load repositories and reported a connection error: they
  looked for the security certificates where the machine that built them kept them. The
  certificates now come with the app.

## [1.1.0] - 2026-09-18

### Added
- After a card is saved, the status line offers a link to star Vetrina on GitHub; once
  it has been followed, it is not shown again.

## [1.0.0] - 2026-09-18

First release.

### Added
- Load a public GitHub repository from its `owner/name` or its link: title, description,
  contributors, issues, stars, forks, languages and owner avatar.
- Live preview, with every field editable and character counters.
- Formats for GitHub (1280 × 640), LinkedIn (1200 × 627), Open Graph (1200 × 630) and X (1200 × 675).
- Light and dark cards; bottom bar in the colors of the languages or in one color.
- Picture chosen from a file or dropped on the window.
- Full-size preview, and PNG export drawn at twice the size for smooth edges.
- Window in Italian, English, Spanish, French and German, light or dark.
- macOS disk image (`.dmg`) and Windows executable (`.exe`), built on every release.
