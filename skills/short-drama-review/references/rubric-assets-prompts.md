# Assets And Asset-Image Prompt Rubric

## Occurrence and decision

- Does every extracted occurrence point to a source block/hash?
- Is it production-relevant rather than every noun in the screenplay?
- Is the decision explicit: reuse, new identity, new variant, or unresolved?
- Were pronouns, aliases, groups, memories, portraits, and screen content handled
  without guessing?

## Identity versus variant

### Character / Look

Identity: stable face/body/hair anchors, distinguishing marks, voice/behavioral
identity. Look: wardrobe, makeup, hair arrangement, injury, dirt/wetness, disguise,
age/weathering state, validity range.

Fail when a costume change creates a new person or incompatible Looks mix in one
prompt without story reason.

Relationship labels may guide current blocking, gaze, and social presentation,
but they do not prove beauty, ugliness, body type, skin tone, or facial morality.
Fail when protagonist/antagonist status silently invents those identity traits;
creator-approved idealization or deliberate counter-casting remains a taste choice.

### Location / View

Identity: architecture, layout, entrances, zones, anchors, materials, navigation.
View: camera-facing orientation/zone, time/weather/light state, visible anchors.

Fail when each camera angle becomes a new unrelated location or geography changes
silently between scene and plate.

Views of one Location sharing a time/weather state must also share key-light source,
warm/cool priority, contrast direction, and practical on/off state (`IMG-10`). Compare
the group side by side—each plate reading well alone is not evidence. Fail when an
unrecorded difference would read as two times or two rooms once the plates are
intercut; orientation-driven back/front lighting and occlusion shadows are expected
and need only a stated source.

### Prop / State

Identity: scale, shape, material, function, moving parts, marks, text policy.
State: owner/hand/location, open/closed, clean/damaged/wet/bloodied, contents,
validity.

Fail when a prop teleports, changes scale/material, or readable evidence is erased.

## Prompt recipe review

All prompt types need purpose, exact binding, identifying facts, current variant,
composition, background, lighting, text policy, constraints, and exclusions. Then
apply type-specific criteria:

- Does each media reference declare one purpose, the facts it may copy,
  the facts it must not import, and a pixel/text admission decision?
- If a reference is composition-, scale-, or effect-only, did the prompt avoid
  borrowing its identity, wardrobe, content, text, count, or story state?

- **Character sheet:** one identity and coherent Look; useful reference views;
  neutral enough background/light to recognize anchors; no story action chain.
- **Location plate:** navigable geography, orientation, fixed anchors, material,
  palette, light direction, atmosphere; normally empty of cast.
- **Prop plate:** scale cue, shape, materials, wear, function/moving parts, current
  state, viewing angle, isolation, text policy.
- **Edit delta:** exact target/hash/region, changes, preserve set, expected
  continuity impact; no unrelated regeneration. Did it start on the minimal-change
  lane, change one thing, and pair every removal with what fills the gap
  (`IMG-16`)? A view change must spell out the new object arrangement object by
  object rather than only naming the new angle.
- **Capability lane:** is the declared lane a capability description kept in the
  metadata, rather than a vendor or model name, and absent from delivery text
  (`IMG-15`)?
- **Palette, light, register:** does the three-band palette state real hue names and
  trace its split to creator instruction, scene content, or an accepted reference?
  Does lighting name key source, direction, ratio, and falloff instead of a mood
  adjective (`IMG-13`)? Cite the diluted anchor rather than a word count (`IMG-14`).

## Performance master profile

- Does each recurring character carry exactly one cross-episode profile, with later
  behavioural change recorded as a continuity delta rather than a second profile
  (`AST-08`)?
- Does every tic name its trigger, and does the profile carry at least one mask with
  the exact condition that cracks it (`AST-09`)?
- Is eye life stated—gaze targeting, blink quality tied to state, live catchlights,
  eyes arriving before the head (`AST-10`)? Its absence survives frame review, so
  check the profile rather than the frames.
- Is the voice prompt a fixed record reused verbatim wherever the character speaks,
  with scene-level breath, volume, and emotion kept out of it (`AST-11`)?
- Does the profile stay free of wardrobe, camera, colour, and this scene's objective?
- Could two characters' profiles be swapped by changing the names?

## Prompt quality failures

- quality/style boilerplate appears before or instead of identity/geography/scale;
- prompt copies the whole 设定集 rather than the needed variant;
- character description mixes immutable anchors with accidental pose;
- location prose is rich but cannot orient entrances/zones;
- one character or prop is assigned to mutually exclusive positions, hands, or
  relationship lines in the same frozen instant;
- prop has no scale or text state;
- negative constraints contradict the required visible fact;
- edit request says “make better” without target/change/preserve;
- rendered Markdown differs from accepted structured spec;
- private URL, source ID, provider task field, or operator complaint leaks in.
- “use the whole reference” does not say what may or may not be copied.

Prompt prose elegance is secondary to recognition, reuse, continuity, and clear
control of the current operation.
