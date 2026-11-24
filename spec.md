# Beam Designer

## Purpose
A beam design tool for engineers and students. The user sets up a beam,
places loads on it, and picks a steel or lumber section. The app shows the
shear, moment, and deflection diagrams and checks whether the beam is
strong and stiff enough, updating instantly as anything changes.

## Platform and implementation
- Build the application in Python as a desktop application using the
  standard-library Tkinter GUI toolkit.
- Use Tkinter widgets for the controls, input panels, check cards, and
  status messages. Use a Tkinter Canvas for the beam drawing, load arrows,
  reactions, diagrams, labels, and synchronized hover crosshair.
- Keep the calculation and validation logic separate from the Tkinter view
  so it can be tested independently.
- Launch the application in a resizable desktop window with a minimum size
  that preserves the two-column layout. On narrower windows, retain the
  desktop arrangement and allow horizontal scrolling rather than stacking
  the panels for phone layouts.

## Users
A civil engineering student checking a homework beam, or an engineer
sizing a floor beam or deck joist.

## Inputs
- Support type: Simply supported or Cantilever (fixed at the left end).
- Span: 4 to 40 ft, set with a slider and a number box that stay in sync.
- Loads, listed in a panel where each can be edited or removed:
  - Point loads: magnitude (kips, downward positive) and position (ft).
    A new point load starts at midspan (at the free end of a cantilever).
  - Uniform loads: magnitude (kips/ft, downward positive) and start and
    end positions (ft).
  - "Add point load" and "Add uniform load" buttons.
  - Point loads can also be dragged along the beam in the drawing,
    snapping to 0.25 ft.
  - Load positions are measured from the left end. Point loads outside the
    span are placed at the nearest beam end; uniform-load intervals are
    clipped to the beam. A uniform load with end <= start is invalid and
    must show an error instead of being silently reordered.
  - Load magnitudes are nonnegative; upward loads are not supported.
- Material and section, from these tables:

  Steel W-shapes (E = 29,000 ksi, allowable bending stress Fb = 30 ksi):

  | Section | Ix (in^4) | Sx (in^3) | Weight (lb/ft) |
  |---------|-----------|-----------|----------------|
  | W8x10   | 30.8      | 7.81      | 10 |
  | W10x12  | 53.8      | 10.9      | 12 |
  | W12x26  | 204       | 33.4      | 26 |
  | W14x22  | 199       | 29.0      | 22 |
  | W16x26  | 301       | 38.4      | 26 |
  | W18x35  | 510       | 57.6      | 35 |
  | W21x44  | 843       | 81.6      | 44 |
  | W24x55  | 1350      | 114       | 55 |

  Douglas Fir-Larch No. 2 lumber (E = 1,600 ksi, Fb = 0.900 ksi):

  | Section | Ix (in^4) | Sx (in^3) |
  |---------|-----------|-----------|
  | 2x8     | 47.63     | 13.14     |
  | 2x10    | 98.93     | 21.39     |
  | 2x12    | 177.98    | 31.64     |

- Deflection limit: L/240 or L/360 (default L/360).
- Self-weight is ignored.

## Sign conventions and units
- The x coordinate starts at the left end and increases to the right.
- Applied point and uniform loads are positive downward. Vertical reactions
  are positive upward. A fixed-end reaction moment is positive
  counterclockwise.
- Positive internal shear acts upward on the left face of a cut. Positive
  bending moment is sagging; negative moment is hogging.
- Deflection y is positive downward. With this convention, use
  EI d^2y/dx^2 = -M, with consistent units.
- Statics and diagrams use kips, feet, and kip-ft. Convert M from kip-ft
  to kip-in by multiplying by 12 for bending stress. For deflection,
  convert x to inches and use E in ksi and I in in^4, so EI is kip-in^2.
- Report signed diagram values, but use maximum absolute shear, moment,
  and deflection magnitudes for maxima and checks.

## Calculations
- Reactions from statics.
- Shear V(x) and moment M(x) along the beam, at 1 ft spacing or finer,
  plus exactly at every load point and load start/end.
- Evaluate shear on both sides of every point load because shear is
  discontinuous there. Use interpolation or solve for extrema between
  samples so the reported maxima and their locations are not limited to
  the plotted sample spacing.
- Deflection y(x) by integrating M/EI twice with the boundary conditions
  for the support type (y = 0 at both supports; or y = 0 and slope = 0 at
  the fixed end). Include interior extrema where slope is zero, as well as
  endpoints, when finding maximum deflection.
- Bending stress fb = |Mmax| * 12 / Sx (ksi), where Mmax is in kip-ft
  and Sx is in in^3. Bending check passes if
  fb <= Fb.
- Deflection check passes if |y|max <= L/240 or L/360 (L in inches).
- Lightest passing section: of the sections in the chosen material, the
  lightest steel section that passes both checks (if two weigh the same,
  the one with the larger Ix), or the first listed lumber size that passes.
  If no section passes, say so and do not suggest a section.
- Units: kips, ft, and kip-ft on screen; inches for deflection.

## Outputs
- A beam drawing with the supports, load arrows (point loads as single
  arrows, uniform loads as a row of small arrows), and the reactions.
- Three diagrams stacked under the beam and lined up with it on the same
  x scale: shear (kips), moment (kip-ft), and deflected shape (in). Each
  diagram is filled and shows its maximum value labeled at its location.
- Moving the mouse over any diagram shows a vertical line across all three
  with the values of V, M, and y at that x.
- Two check cards: Bending and Deflection. Each shows the actual value, the
  allowable value, a bar for the ratio (green under 70%, amber 70-100%,
  red over 100%), and PASS or FAIL.
- A line suggesting the lightest passing section, with a button to use it.
- Everything updates immediately whenever any input changes.
- An "Export results" button saves a CSV table with x, shear V, moment M,
  and deflection values along the beam for use in Excel.
- A "Calculation sheet" button saves a PDF containing the inputs, diagrams,
  design checks, and scope disclaimer in a hand-in-ready layout.
- Show a prominent note that PASS only means the beam meets the simplified
  bending and deflection checks in this app; it is not a complete or
  code-compliant design.

## Look and feel
- Opens with an example already loaded (20 ft simply supported W12x26
  with a 1 kip/ft uniform load over the full span), so it is useful the
  moment it opens.
- Use a BYU-inspired blue-and-white palette and include the text
  "Brigham Young University" as a subtle background watermark or header
  treatment. Can use an official logo or seal.
- Use Georgia as the primary font, with "Times New Roman", serif fallbacks.
- Design for desktop and laptop computers, with a wide two-column layout:
  inputs on the left and the beam, diagrams, and checks on the right. Do not
  stack the panels for phone layouts; on narrower viewports, retain the
  desktop layout and allow horizontal scrolling.
- Frame the page and major cards with prominent, carved-wood-like borders
  inspired by Neo-Gothic architecture. Use visible wood grain, layered
  molding, pointed arches, and tracery details in dark walnut and warm
  bronze tones. Keep the BYU-inspired blue-and-white surfaces inside the
  frames, and preserve clear contrast and legibility.
- Keep the overall interface clean and professional inside the ornate
  frames, with a light background, white cards, and generous spacing.
- Inputs in a panel on the left; drawing, diagrams, and checks on the
  right, optimized for a desktop screen.
- Every input has a short label with units. Hovering over a check card
  explains the formula used.
- Keep the simplified-design disclaimer visible at all viewport sizes.

## Validation
1. Simply supported, 20 ft, W12x26, uniform 1 kip/ft over the full span:
   reactions 10 k and 10 k; max shear 10 k; max moment 50.0 kip-ft at
   10 ft; fb = 17.96 ksi; max deflection 0.609 in at 10 ft; L/360 =
   0.667 in; both checks pass.
2. Simply supported, 20 ft, W12x26, point load 10 k at 5 ft: reactions
   7.5 k (left) and 2.5 k (right); max moment 37.5 kip-ft at 5 ft;
   fb = 13.47 ksi; max deflection 0.340 in at 8.82 ft.
3. Cantilever, 10 ft, W12x26, point load 5 k at the free end: reaction
   5 k and fixed-end moment 50 kip-ft; max deflection 0.487 in at the free
   end (PL^3/3EI); L/360 = 0.333 in, so deflection fails.
4. Simply supported 12 ft 2x10 joist, uniform 0.05 kip/ft: max moment
   0.90 kip-ft; fb = 0.505 ksi; max deflection 0.147 in; both pass.
5. Also validate clipping of loads at the beam ends, an invalid uniform
   interval (end <= start), zero applied load, and shear values on both
   sides of a point load.

## Implementation stages and exit checks
Complete and test each stage before starting the next. Stage 1 is a static
mockup only; later stages add behavior incrementally.

1. **Static layout mockup (no calculations)**
   - Build the desktop-focused Tkinter window layout with fixed example inputs and
     placeholder beam, diagrams, checks, and section recommendation.
   - Apply the BYU-inspired blue-and-white treatment, Georgia typography,
     and prominent carved-wood Neo-Gothic frames.
   - **Exit check:** Review at a desktop window at least 1280 px wide.
     Confirm inputs stay on the left, results stay on the right, and the
     ornate borders do not crowd labels, diagrams, or the disclaimer.
2. **Inputs and load editing**
   - Wire span controls, support/material/section/limit selectors, load
     add/edit/remove controls, and point-load dragging with 0.25-ft
     snapping. Keep calculated results as placeholders.
   - **Exit check:** Confirm span slider and number box stay synchronized;
     add, edit, and remove both load types; drag a point load; and verify
     invalid uniform-load intervals show an error without being reordered.
3. **Reactions, shear, and moment**
   - Implement statics and the shear and moment diagrams using the stated
     sign conventions, load clipping rules, and point-load discontinuities.
   - **Exit check:** Compare reactions and diagrams against validation
     cases 1-4. Check shear on both sides of point loads and maxima between
     plotted samples.
4. **Deflection and design checks**
   - Implement deflection integration and support boundary conditions,
     bending stress, deflection limits, check ratios, and pass/fail states.
   - **Exit check:** Compare all four validation cases, including case 2's
     maximum deflection near 8.82 ft and case 3's 0.487-in cantilever
     deflection and deflection failure.
5. **Passing-section recommendation**
   - Evaluate the sections in the selected material, apply the steel
     weight/tie-break rule or lumber table order, and wire up the button to
     use the recommended section.
   - **Exit check:** Verify the default example's steel recommendation
     and confirm whether 2x8 is the first passing lumber option for
     validation case 4.
6. **Crosshair and final integration**
   - Add synchronized hover values across the diagrams, formula
     explanations, labeled maxima, desktop layout and accessibility
     refinements, and the persistent scope disclaimer.
   - **Exit check:** Hover at several x positions and confirm the readout
     matches all diagrams at the same location. Rerun validation cases and
     review keyboard use and the desktop layout at the target viewport.

## Out of scope
- Self-weight, shear stress, lateral-torsional buckling, load
  combinations, and continuous beams.
- The app does not verify connections, local buckling, code load
  combinations, or other omitted design requirements. Results are for
  learning and preliminary checks and require independent professional
  review before they are used for an actual structure.
