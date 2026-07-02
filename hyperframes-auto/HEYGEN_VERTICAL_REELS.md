# HeyGen Vertical Reels Rule

Use this rule for every vertical HeyGen source video in this project.

## Format

- Composition is always `1080x1920`.
- Output is always `9:16`.
- The HeyGen video remains the base layer and keeps its original audio.
- Overlays are editorial cutaways, not full replacement scenes.

## Director

- Target overlay coverage is about `50%` of the video duration.
- The director adds about `0.75s` of hold time to each card so viewers can read the slide and visual.
- Keep clean avatar/video gaps between cutaways when possible.
- Prefer avatar visibility over excessive slide density.
- Every overlay must advance the spoken story: hook, conflict, consequence, proof, or conclusion.

## Card Design

- Vertical HeyGen overlays use one stable lower dock by default:
  - width: `984px`
  - height: `320px`
  - left: `48px`
  - top: `1210px`
  - same position for every scene
- Do not move the card between corners or cover the speaker's face.
- Keep the dock as deterministic HTML/CSS:
  - kicker
  - headline
  - optional subtitle
  - compact infographic: metric, bars, flow, or keyword pills
- Do not show technical production comments such as why the visual supports the face or the scene.
- Avoid long explanatory labels. The overlay should summarize the spoken point, not compete with the narration.
- If a card is a quote or author interpretation, name the source/context only when that helps the viewer.
- To restore the legacy large-card image mode, set `HYPERFRAMES_VERTICAL_DOCK_CARDS=false`.

## Visual Block

- The right side of the dock is the main infographic.
- Prefer native HTML graphics when the point is simple:
  - metric/value cards for one strong number
  - bar comparisons for `before/after` or `base/target`
  - flow boxes for process or cause/effect
  - keyword pills for compact concept clusters
- Generate a visual image only in legacy large-card mode.
- A generated image must:
  - use a square `1:1` composition so the visual can occupy more vertical card space
  - make the main object/metaphor large and readable, filling most of the frame
  - use stronger real-world associations when useful: national flags, people, ships, ports, oil objects, documents, borders, checkpoints, bridges, shields, and other concrete editorial symbols
  - stay on a white or near-white background
  - match the red/navy editorial style
  - avoid repeating the card headline/subtitle
  - avoid tiny labels and decorative clutter
  - visualize relationships and consequences, not isolated nouns

## AI Image Pipeline

1. Prepare the new HeyGen source video. This copies it to `assets/input/source.mp4`, reads duration/FPS with `ffprobe`, updates `index.html`, and resets old generated image slots:

   ```bash
   npm run prepare:heygen -- --video /absolute/path/to/new-heygen-video.mp4
   ```

   For the same video when you only want to keep existing generated images:

   ```bash
   npm run prepare:heygen -- --keep-images
   ```

2. Build or update the HTML cards from the transcript/scene plan.
3. Run the timeline director. It reads the composition duration and word-level transcript if present, then places cutaways around the video with about 50% overlay coverage:

   ```bash
   npm run direct:timeline
   ```

4. Run:

   ```bash
   npm run generate:prompts
   ```

5. Generate the visual blocks through Kie.ai GPT Image 2:

   ```bash
   KIE_API_KEY=... npm run generate:images
   ```

6. The image generator saves `assets/generated/beat-N.png` and enables those IDs in `data-generated-images`.
7. Run:

   ```bash
   npm run check
   ```

## Prompt Rule

Prompts are generated from the actual card content in `index.html`.

Each prompt should produce only the lower infographic image, because the title/subtitle remain HTML.
The prompt should follow this semantic model:

```text
subject -> action -> obstacle -> result
```

For weak visuals, improve the `data-visual-brief` on the corresponding `<section>` instead of redesigning the whole card.

## Variable Duration Rule

Never hardcode duration for a new HeyGen video by hand.

Every source video has its own duration and often its own FPS. Always run `npm run prepare:heygen` first so these fields are synced automatically:

- root composition `data-duration`
- source video `data-duration`
- root `data-fps`
- `totalDuration` used by the director coverage calculation

Then the timeline director must place cutaways against the new transcript/scene plan, keeping the same design rules and about 50% overlay coverage.

The timeline director is implemented as:

```bash
npm run direct:timeline
```

It updates every `beat-*` section's `data-start` and `data-duration`. If word timings exist in `assets/input/transcript.deepgram.json`, it uses them as anchors; otherwise it falls back to an even distribution across the source duration.
