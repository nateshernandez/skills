# UX checklist: this project

- The design system is `docs/design/guide.md`; judge every screen against its layout and pattern rules, and cite the line a screen breaks
- Tokens live only in `<tokens file>`; components in `<components folder>`; a hand-rolled control the folder already has is a blocker
- Density is <body px> text and <control px> controls on desktop; under 44px on a touch screen is a blocker
- The look is <one line from look.md>; a screen that reads as another app's is a note, naming the token or layout it skipped
