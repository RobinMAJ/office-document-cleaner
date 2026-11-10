# Office Cleaner visual direction

Requested direction: Apple-like, Chinese-first, approachable desktop utility with legible mobile controls.

Tokens: canvas #f5f5f7; surface #ffffff; primary text #1d1d1f; supporting text #515154; separators #e5e5ea; action blue #0071e3; success #167849. System typography (-apple-system / PingFang SC) with clear type scale and 1.5–1.6 body leading. No remote font requests.

Layout: one compact system-like toolbar; a purposeful title; left column for file selection and cleanup scope; right property inspector grouped by people, dates, description and software; one sticky output action bar. Roundings vary by hierarchy (18 px work surfaces, 9 px controls, 5 px small elements). A light translucent toolbar only, with opaque document controls for reliable contrast.

Interaction: press feedback begins immediately; dragging highlights the drop target; switching a cleanup option or field gives direct feedback; changes can be reverted without altering the source file. No artificial delays, entrance animation or looping decoration. Keyboard focus, 44 px touch targets, reduced-motion and reduced-transparency included.

Reference skill: https://github.com/emilkowalski/apple-design ; local copy read from Chili's existing skill package. Implementation uses native HTML/CSS and original document-processing functions; no animation framework required for this utility.
