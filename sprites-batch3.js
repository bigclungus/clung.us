// sprites-batch3.js — Pixel art sprite variants for bloodfeast, adelbert, jhaddu, morgan, the-kid
// Each function: cx = horizontal center, cy = bottom edge. fillRect only. ~40px tall, ~20px wide.

// ─── BLOODFEAST (Holden Bloodfeast) — #dc2626 ────────────────────────────────

function drawSprite_bloodfeast_A(ctx, cx, cy) {
  // Geriatric Hawk — military uniform, medals, gray hair, ramrod posture
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Boots
  ctx.fillStyle = '#1a0a0a';
  ctx.fillRect(x + 4, y + 36, 4, 4);
  ctx.fillRect(x + 12, y + 36, 4, 4);

  // Legs — dark navy trousers
  ctx.fillStyle = '#1c2a4a';
  ctx.fillRect(x + 5, y + 28, 4, 8);
  ctx.fillRect(x + 11, y + 28, 4, 8);

  // Trouser stripe (gold)
  ctx.fillStyle = '#c8a020';
  ctx.fillRect(x + 6, y + 28, 1, 8);
  ctx.fillRect(x + 13, y + 28, 1, 8);

  // Body — military green jacket
  ctx.fillStyle = '#2d4a1e';
  ctx.fillRect(x + 3, y + 16, 14, 14);

  // Collar / shirt (white)
  ctx.fillStyle = '#d0d0d0';
  ctx.fillRect(x + 8, y + 16, 4, 3);

  // Medals row (three colored dots on chest)
  ctx.fillStyle = '#c8a020'; // gold
  ctx.fillRect(x + 4, y + 19, 2, 2);
  ctx.fillRect(x + 7, y + 19, 2, 2);
  ctx.fillStyle = '#dc2626'; // red ribbon
  ctx.fillRect(x + 4, y + 21, 2, 1);
  ctx.fillRect(x + 7, y + 21, 2, 1);
  ctx.fillStyle = '#4a90c8'; // blue ribbon
  ctx.fillRect(x + 10, y + 19, 2, 2);
  ctx.fillRect(x + 10, y + 21, 2, 1);

  // Epaulettes (gold shoulder boards)
  ctx.fillStyle = '#c8a020';
  ctx.fillRect(x + 2, y + 16, 3, 2);
  ctx.fillRect(x + 15, y + 16, 3, 2);

  // Neck
  ctx.fillStyle = '#b87858';
  ctx.fillRect(x + 8, y + 12, 4, 5);

  // Head — narrow, stern
  ctx.fillStyle = '#c49060';
  ctx.fillRect(x + 6, y + 6, 8, 8);

  // Gray hair (short, cropped)
  ctx.fillStyle = '#a0a0a8';
  ctx.fillRect(x + 6, y + 6, 8, 2);
  ctx.fillRect(x + 6, y + 8, 1, 2);
  ctx.fillRect(x + 13, y + 8, 1, 2);

  // Eyes — steely, small
  ctx.fillStyle = '#4a6080';
  ctx.fillRect(x + 7, y + 10, 2, 1);
  ctx.fillRect(x + 11, y + 10, 2, 1);

  // Brow ridge (stern)
  ctx.fillStyle = '#8a6844';
  ctx.fillRect(x + 7, y + 9, 2, 1);
  ctx.fillRect(x + 11, y + 9, 2, 1);

  // Thin line mouth (no smile)
  ctx.fillStyle = '#8a5a3a';
  ctx.fillRect(x + 8, y + 12, 4, 1);

  // Military cap
  ctx.fillStyle = '#2d4a1e';
  ctx.fillRect(x + 5, y + 4, 10, 3);
  ctx.fillRect(x + 4, y + 5, 12, 2);

  // Cap brim
  ctx.fillStyle = '#1a2e0e';
  ctx.fillRect(x + 3, y + 7, 14, 1);

  // Cap insignia (gold)
  ctx.fillStyle = '#c8a020';
  ctx.fillRect(x + 9, y + 5, 2, 1);

  // Arms — at sides, rigid
  ctx.fillStyle = '#2d4a1e';
  ctx.fillRect(x + 1, y + 17, 3, 10);
  ctx.fillRect(x + 16, y + 17, 3, 10);

  // Hands
  ctx.fillStyle = '#c49060';
  ctx.fillRect(x + 1, y + 27, 3, 2);
  ctx.fillRect(x + 16, y + 27, 3, 2);
}

function drawSprite_bloodfeast_B(ctx, cx, cy) {
  // Cold War Hawk — 1960s suit, tie, holding red phone, suspicious look
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Shoes
  ctx.fillStyle = '#1a1a1a';
  ctx.fillRect(x + 4, y + 36, 5, 4);
  ctx.fillRect(x + 11, y + 36, 5, 4);

  // Trousers (charcoal)
  ctx.fillStyle = '#3a3a4a';
  ctx.fillRect(x + 5, y + 26, 4, 10);
  ctx.fillRect(x + 11, y + 26, 4, 10);

  // Suit jacket (dark charcoal)
  ctx.fillStyle = '#2a2a3a';
  ctx.fillRect(x + 3, y + 14, 14, 13);

  // Lapels (lighter charcoal)
  ctx.fillStyle = '#3c3c50';
  ctx.fillRect(x + 7, y + 14, 3, 6);
  ctx.fillRect(x + 10, y + 14, 3, 6);

  // White shirt strip in center
  ctx.fillStyle = '#e0e0e0';
  ctx.fillRect(x + 9, y + 14, 2, 4);

  // Tie — red (thin)
  ctx.fillStyle = '#dc2626';
  ctx.fillRect(x + 9, y + 14, 2, 7);
  ctx.fillRect(x + 9, y + 21, 2, 2); // tie knot
  ctx.fillRect(x + 10, y + 23, 1, 3); // tie tail

  // Neck
  ctx.fillStyle = '#c49060';
  ctx.fillRect(x + 8, y + 11, 4, 4);

  // Head (suspicious narrow eyes)
  ctx.fillStyle = '#c49060';
  ctx.fillRect(x + 6, y + 5, 8, 8);

  // Brown hair, slicked
  ctx.fillStyle = '#5a3a20';
  ctx.fillRect(x + 6, y + 5, 8, 2);
  ctx.fillRect(x + 6, y + 7, 1, 1);
  ctx.fillRect(x + 13, y + 7, 1, 1);

  // Eyes — narrowed (suspicious)
  ctx.fillStyle = '#3a3020';
  ctx.fillRect(x + 7, y + 9, 2, 1);
  ctx.fillRect(x + 11, y + 9, 2, 1);
  // shadow under brow
  ctx.fillStyle = '#9a7050';
  ctx.fillRect(x + 7, y + 8, 2, 1);
  ctx.fillRect(x + 11, y + 8, 2, 1);

  // Thin lips pressed
  ctx.fillStyle = '#8a5a3a';
  ctx.fillRect(x + 8, y + 11, 4, 1);

  // Left arm (holding phone)
  ctx.fillStyle = '#2a2a3a';
  ctx.fillRect(x + 0, y + 15, 3, 9);
  ctx.fillRect(x + 0, y + 22, 4, 3); // forearm out
  // Hand
  ctx.fillStyle = '#c49060';
  ctx.fillRect(x + 0, y + 24, 3, 3);

  // Red phone (in hand, left side)
  ctx.fillStyle = '#dc2626';
  ctx.fillRect(x - 2, y + 22, 4, 6);
  // phone receiver shape
  ctx.fillStyle = '#ff4444';
  ctx.fillRect(x - 2, y + 22, 4, 2);
  ctx.fillRect(x - 2, y + 26, 4, 2);
  ctx.fillStyle = '#aa1010';
  ctx.fillRect(x - 1, y + 24, 2, 2);

  // Right arm (down at side)
  ctx.fillStyle = '#2a2a3a';
  ctx.fillRect(x + 17, y + 15, 3, 11);
  ctx.fillStyle = '#c49060';
  ctx.fillRect(x + 17, y + 26, 3, 2);
}

function drawSprite_bloodfeast_C(ctx, cx, cy) {
  // Committeeman — congressional seat pose, flag pin on lapel, notes in hand
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Seat base (simple chair suggestion)
  ctx.fillStyle = '#4a3a28';
  ctx.fillRect(x + 2, y + 30, 16, 2); // seat surface
  ctx.fillRect(x + 3, y + 32, 3, 8);  // left leg
  ctx.fillRect(x + 14, y + 32, 3, 8); // right leg

  // Chair back
  ctx.fillStyle = '#5a4a32';
  ctx.fillRect(x + 2, y + 16, 2, 15);

  // Trousers
  ctx.fillStyle = '#1c2a4a';
  ctx.fillRect(x + 5, y + 26, 5, 5);
  ctx.fillRect(x + 10, y + 26, 5, 5);

  // Suit jacket (navy)
  ctx.fillStyle = '#1c2a4a';
  ctx.fillRect(x + 4, y + 14, 12, 13);

  // White shirt / collar
  ctx.fillStyle = '#e0e0e0';
  ctx.fillRect(x + 8, y + 14, 4, 3);

  // Lapels
  ctx.fillStyle = '#253a60';
  ctx.fillRect(x + 6, y + 14, 3, 5);
  ctx.fillRect(x + 11, y + 14, 3, 5);

  // Flag pin (small on left lapel)
  ctx.fillStyle = '#dc2626';
  ctx.fillRect(x + 6, y + 17, 2, 1);
  ctx.fillStyle = '#e0e0e0';
  ctx.fillRect(x + 6, y + 18, 2, 1);
  ctx.fillStyle = '#3060c0';
  ctx.fillRect(x + 6, y + 19, 2, 1);

  // Neck
  ctx.fillStyle = '#c49060';
  ctx.fillRect(x + 8, y + 11, 4, 4);

  // Head
  ctx.fillStyle = '#c49060';
  ctx.fillRect(x + 6, y + 4, 8, 8);

  // Gray hair (distinguished)
  ctx.fillStyle = '#b0b0b8';
  ctx.fillRect(x + 6, y + 4, 8, 2);
  ctx.fillRect(x + 6, y + 6, 1, 2);
  ctx.fillRect(x + 13, y + 6, 1, 2);

  // Eyes — formal, steady
  ctx.fillStyle = '#4a3820';
  ctx.fillRect(x + 7, y + 8, 2, 1);
  ctx.fillRect(x + 11, y + 8, 2, 1);

  // Mouth — neutral
  ctx.fillStyle = '#8a5a3a';
  ctx.fillRect(x + 8, y + 11, 4, 1);

  // Right arm extended holding notes
  ctx.fillStyle = '#1c2a4a';
  ctx.fillRect(x + 16, y + 16, 3, 8);
  ctx.fillRect(x + 16, y + 23, 5, 3); // forearm forward

  // Notes (white rectangle in hand)
  ctx.fillStyle = '#f0f0f0';
  ctx.fillRect(x + 18, y + 20, 5, 7);
  // line marks on notes
  ctx.fillStyle = '#c0c0c0';
  ctx.fillRect(x + 19, y + 22, 3, 1);
  ctx.fillRect(x + 19, y + 24, 3, 1);

  // Left arm on table/resting
  ctx.fillStyle = '#1c2a4a';
  ctx.fillRect(x + 1, y + 16, 3, 10);
  ctx.fillStyle = '#c49060';
  ctx.fillRect(x + 1, y + 26, 3, 2);
}

// ─── ADELBERT (Adelbert Hominem) — #94a3b8 ───────────────────────────────────

function drawSprite_adelbert_A(ctx, cx, cy) {
  // Internet Troll — hunched, laptop, glasses reflecting screen, smug grin
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Chair legs
  ctx.fillStyle = '#3a3040';
  ctx.fillRect(x + 2, y + 34, 2, 6);
  ctx.fillRect(x + 14, y + 34, 2, 6);

  // Seat
  ctx.fillStyle = '#4a405a';
  ctx.fillRect(x + 1, y + 31, 16, 3);

  // Legs (rumpled jeans)
  ctx.fillStyle = '#2a3050';
  ctx.fillRect(x + 4, y + 28, 5, 6);
  ctx.fillRect(x + 9, y + 28, 5, 6);

  // Body — hunched, t-shirt (muted gray)
  ctx.fillStyle = '#5a5868';
  ctx.fillRect(x + 3, y + 17, 14, 13);

  // Hunch — shoulders curved forward
  ctx.fillStyle = '#4a4858';
  ctx.fillRect(x + 3, y + 17, 2, 4);
  ctx.fillRect(x + 15, y + 17, 2, 4);

  // Laptop (open, on lap)
  ctx.fillStyle = '#2a2a3a';
  ctx.fillRect(x + 3, y + 26, 12, 7);  // base
  ctx.fillRect(x + 4, y + 19, 12, 8);  // screen open upward

  // Screen glow (blue-white)
  ctx.fillStyle = '#8ab8e0';
  ctx.fillRect(x + 5, y + 20, 10, 6);

  // Screen reflection in glasses (handled below)

  // Neck
  ctx.fillStyle = '#9a8878';
  ctx.fillRect(x + 8, y + 13, 4, 5);

  // Head
  ctx.fillStyle = '#a89880';
  ctx.fillRect(x + 6, y + 6, 8, 8);

  // Disheveled hair
  ctx.fillStyle = '#3a2a18';
  ctx.fillRect(x + 6, y + 6, 8, 2);
  ctx.fillRect(x + 5, y + 7, 2, 3);
  ctx.fillRect(x + 13, y + 7, 2, 2);
  ctx.fillRect(x + 7, y + 6, 1, 1); // cowlick

  // Glasses frame
  ctx.fillStyle = '#2a2a2a';
  ctx.fillRect(x + 6, y + 9, 3, 2);
  ctx.fillRect(x + 11, y + 9, 3, 2);
  ctx.fillRect(x + 9, y + 10, 2, 1); // bridge

  // Lens glow (screen reflected)
  ctx.fillStyle = '#7ab0d8';
  ctx.fillRect(x + 7, y + 9, 2, 2);
  ctx.fillRect(x + 11, y + 9, 2, 2);

  // Smug grin
  ctx.fillStyle = '#7a5a3a';
  ctx.fillRect(x + 7, y + 12, 5, 1);
  ctx.fillRect(x + 11, y + 12, 1, 1); // smirk corner

  // Arms reaching to keyboard
  ctx.fillStyle = '#5a5868';
  ctx.fillRect(x + 2, y + 18, 3, 8);
  ctx.fillRect(x + 15, y + 18, 3, 8);
  // hands on keyboard
  ctx.fillStyle = '#a89880';
  ctx.fillRect(x + 2, y + 25, 3, 2);
  ctx.fillRect(x + 15, y + 25, 3, 2);
}

function drawSprite_adelbert_B(ctx, cx, cy) {
  // Armchair Philosopher — large armchair drawn, pointing upward making a point
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Armchair — large, worn
  // Chair back (tall)
  ctx.fillStyle = '#6a4a2a';
  ctx.fillRect(x + 0, y + 6, 3, 30);   // left back post
  ctx.fillRect(x + 17, y + 6, 3, 30);  // right back post
  ctx.fillRect(x + 0, y + 6, 20, 4);   // top rail

  // Chair cushion back fill
  ctx.fillStyle = '#8a6040';
  ctx.fillRect(x + 3, y + 10, 14, 20);

  // Armrests
  ctx.fillStyle = '#7a5030';
  ctx.fillRect(x + 0, y + 20, 4, 2);
  ctx.fillRect(x + 16, y + 20, 4, 2);

  // Seat cushion
  ctx.fillStyle = '#9a7050';
  ctx.fillRect(x + 1, y + 28, 18, 5);

  // Chair legs
  ctx.fillStyle = '#4a3020';
  ctx.fillRect(x + 1, y + 33, 3, 7);
  ctx.fillRect(x + 16, y + 33, 3, 7);

  // Person sitting in chair
  // Trousers
  ctx.fillStyle = '#3a3a4a';
  ctx.fillRect(x + 5, y + 26, 4, 6);
  ctx.fillRect(x + 11, y + 26, 4, 6);

  // Body — tweed-ish sweater
  ctx.fillStyle = '#6a5a38';
  ctx.fillRect(x + 4, y + 16, 12, 11);

  // Collar
  ctx.fillStyle = '#e0d8c0';
  ctx.fillRect(x + 8, y + 16, 4, 3);

  // Neck
  ctx.fillStyle = '#a89870';
  ctx.fillRect(x + 8, y + 13, 4, 4);

  // Head
  ctx.fillStyle = '#b09870';
  ctx.fillRect(x + 6, y + 6, 8, 8);

  // Hair — thinning, messy
  ctx.fillStyle = '#4a3820';
  ctx.fillRect(x + 6, y + 6, 8, 2);
  ctx.fillRect(x + 14, y + 8, 1, 2);

  // Glasses (round)
  ctx.fillStyle = '#2a2020';
  ctx.fillRect(x + 6, y + 9, 3, 2);
  ctx.fillRect(x + 11, y + 9, 3, 2);
  ctx.fillRect(x + 9, y + 10, 2, 1);
  ctx.fillStyle = '#c8c0a0';
  ctx.fillRect(x + 7, y + 9, 2, 2);
  ctx.fillRect(x + 11, y + 9, 2, 2);

  // Mouth open — making a point
  ctx.fillStyle = '#7a5030';
  ctx.fillRect(x + 8, y + 12, 4, 1);
  ctx.fillRect(x + 9, y + 12, 2, 2); // open mouth

  // Right arm raised, finger pointing up
  ctx.fillStyle = '#6a5a38';
  ctx.fillRect(x + 16, y + 17, 3, 6);
  ctx.fillRect(x + 16, y + 12, 3, 6); // upper arm raised
  ctx.fillStyle = '#b09870';
  ctx.fillRect(x + 16, y + 10, 2, 3); // hand
  ctx.fillRect(x + 17, y + 7, 1, 4);  // finger pointing up

  // Left arm resting on armrest
  ctx.fillStyle = '#6a5a38';
  ctx.fillRect(x + 1, y + 18, 3, 6);
  ctx.fillStyle = '#b09870';
  ctx.fillRect(x + 1, y + 23, 3, 2);
}

function drawSprite_adelbert_C(ctx, cx, cy) {
  // Devil's Advocate — devil horns on head, one angel wing, sly smile
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Shoes
  ctx.fillStyle = '#2a2020';
  ctx.fillRect(x + 4, y + 36, 5, 4);
  ctx.fillRect(x + 11, y + 36, 5, 4);

  // Trousers (dark)
  ctx.fillStyle = '#2a2a3a';
  ctx.fillRect(x + 5, y + 26, 4, 10);
  ctx.fillRect(x + 11, y + 26, 4, 10);

  // Body — casual dark jacket
  ctx.fillStyle = '#1a1a2a';
  ctx.fillRect(x + 3, y + 14, 14, 13);

  // Collar
  ctx.fillStyle = '#94a3b8';
  ctx.fillRect(x + 8, y + 14, 4, 3);

  // Neck
  ctx.fillStyle = '#a08870';
  ctx.fillRect(x + 8, y + 11, 4, 4);

  // Head
  ctx.fillStyle = '#b09870';
  ctx.fillRect(x + 6, y + 5, 8, 8);

  // Hair — dark, slight widow's peak
  ctx.fillStyle = '#2a1818';
  ctx.fillRect(x + 6, y + 5, 8, 2);
  ctx.fillRect(x + 9, y + 4, 2, 2); // widow's peak
  ctx.fillRect(x + 6, y + 7, 1, 2);
  ctx.fillRect(x + 13, y + 7, 1, 2);

  // Devil horns (small red rects on top of head)
  ctx.fillStyle = '#cc2020';
  ctx.fillRect(x + 7, y + 3, 2, 3);
  ctx.fillRect(x + 11, y + 3, 2, 3);
  // horn tips (pointy, one pixel)
  ctx.fillRect(x + 8, y + 2, 1, 1);
  ctx.fillRect(x + 12, y + 2, 1, 1);

  // Angel wing on left side only (white feathered)
  ctx.fillStyle = '#e8e8e8';
  ctx.fillRect(x - 4, y + 12, 5, 8);
  ctx.fillRect(x - 5, y + 15, 4, 5);
  ctx.fillRect(x - 3, y + 10, 3, 4);
  // feather detail lines
  ctx.fillStyle = '#c8c8c8';
  ctx.fillRect(x - 4, y + 14, 5, 1);
  ctx.fillRect(x - 4, y + 17, 5, 1);

  // Eyes — sly, half-lidded
  ctx.fillStyle = '#3a2820';
  ctx.fillRect(x + 7, y + 9, 2, 1);
  ctx.fillRect(x + 11, y + 9, 2, 1);
  // heavy brow
  ctx.fillStyle = '#2a1818';
  ctx.fillRect(x + 7, y + 8, 2, 1);
  ctx.fillRect(x + 11, y + 8, 2, 1);

  // Sly smile (asymmetric)
  ctx.fillStyle = '#7a5030';
  ctx.fillRect(x + 8, y + 12, 4, 1);
  ctx.fillRect(x + 12, y + 11, 1, 1); // smirk side up

  // Right arm — down at side (no wing)
  ctx.fillStyle = '#1a1a2a';
  ctx.fillRect(x + 17, y + 15, 3, 11);
  ctx.fillStyle = '#a08870';
  ctx.fillRect(x + 17, y + 26, 3, 2);

  // Left arm (wing-side, partially hidden)
  ctx.fillStyle = '#1a1a2a';
  ctx.fillRect(x + 0, y + 15, 3, 10);
  ctx.fillStyle = '#a08870';
  ctx.fillRect(x + 0, y + 25, 3, 2);
}

// ─── JHADDU — #fb923c ─────────────────────────────────────────────────────────

function drawSprite_jhaddu_A(ctx, cx, cy) {
  // Enterprise Consultant — expensive suit, luxury watch, confidence, branded laptop
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Shoes (expensive, polished)
  ctx.fillStyle = '#1a0808';
  ctx.fillRect(x + 4, y + 36, 5, 4);
  ctx.fillRect(x + 11, y + 36, 5, 4);
  // shine on shoes
  ctx.fillStyle = '#3a1818';
  ctx.fillRect(x + 5, y + 36, 2, 1);
  ctx.fillRect(x + 12, y + 36, 2, 1);

  // Trousers (premium charcoal pinstripe)
  ctx.fillStyle = '#2a2a30';
  ctx.fillRect(x + 5, y + 26, 4, 10);
  ctx.fillRect(x + 11, y + 26, 4, 10);
  // pinstripe
  ctx.fillStyle = '#3a3a42';
  ctx.fillRect(x + 7, y + 26, 1, 10);
  ctx.fillRect(x + 13, y + 26, 1, 10);

  // Suit jacket (premium charcoal)
  ctx.fillStyle = '#2a2a38';
  ctx.fillRect(x + 3, y + 14, 14, 13);

  // Pocket square (orange, matching brand)
  ctx.fillStyle = '#fb923c';
  ctx.fillRect(x + 13, y + 15, 2, 2);

  // White shirt
  ctx.fillStyle = '#f0f0f0';
  ctx.fillRect(x + 8, y + 14, 4, 4);

  // Lapels
  ctx.fillStyle = '#3a3a4a';
  ctx.fillRect(x + 6, y + 14, 3, 6);
  ctx.fillRect(x + 11, y + 14, 3, 6);

  // Tie (orange power tie)
  ctx.fillStyle = '#fb923c';
  ctx.fillRect(x + 9, y + 14, 2, 8);
  ctx.fillStyle = '#e07020';
  ctx.fillRect(x + 9, y + 15, 2, 2); // tie knot shadow

  // Luxury watch (gold, left wrist)
  ctx.fillStyle = '#c8a020';
  ctx.fillRect(x + 1, y + 25, 4, 3);
  ctx.fillStyle = '#e8c030';
  ctx.fillRect(x + 2, y + 25, 2, 2);

  // Neck
  ctx.fillStyle = '#c09060';
  ctx.fillRect(x + 8, y + 11, 4, 4);

  // Head (confident bearing)
  ctx.fillStyle = '#c8a070';
  ctx.fillRect(x + 6, y + 4, 8, 8);

  // Neat hair (well-groomed)
  ctx.fillStyle = '#2a1808';
  ctx.fillRect(x + 6, y + 4, 8, 2);
  ctx.fillRect(x + 6, y + 6, 1, 1);
  ctx.fillRect(x + 13, y + 6, 1, 1);

  // Eyes (confident, direct)
  ctx.fillStyle = '#3a2010';
  ctx.fillRect(x + 7, y + 8, 2, 2);
  ctx.fillRect(x + 11, y + 8, 2, 2);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(x + 8, y + 8, 1, 1);
  ctx.fillRect(x + 12, y + 8, 1, 1);

  // Confident smile
  ctx.fillStyle = '#8a5a30';
  ctx.fillRect(x + 7, y + 11, 6, 1);
  ctx.fillRect(x + 7, y + 12, 1, 1);
  ctx.fillRect(x + 12, y + 12, 1, 1);

  // Left arm — carrying laptop
  ctx.fillStyle = '#2a2a38';
  ctx.fillRect(x + 0, y + 16, 3, 10);
  ctx.fillRect(x + 0, y + 24, 5, 3);

  // Branded laptop under arm (thin, premium)
  ctx.fillStyle = '#d0d0d0';
  ctx.fillRect(x - 1, y + 26, 7, 4);
  ctx.fillStyle = '#fb923c'; // brand logo
  ctx.fillRect(x + 1, y + 27, 2, 2);

  // Right arm — slightly out, confident posture
  ctx.fillStyle = '#2a2a38';
  ctx.fillRect(x + 17, y + 16, 3, 10);
  ctx.fillStyle = '#c8a070';
  ctx.fillRect(x + 17, y + 26, 3, 2);
}

function drawSprite_jhaddu_B(ctx, cx, cy) {
  // Pattern Evangelist — holding large book titled "Patterns", serene smile
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Shoes
  ctx.fillStyle = '#2a1808';
  ctx.fillRect(x + 4, y + 36, 5, 4);
  ctx.fillRect(x + 11, y + 36, 5, 4);

  // Trousers (warm tan)
  ctx.fillStyle = '#8a7050';
  ctx.fillRect(x + 5, y + 26, 4, 10);
  ctx.fillRect(x + 11, y + 26, 4, 10);

  // Body — relaxed blazer (warm orange-tan)
  ctx.fillStyle = '#c07840';
  ctx.fillRect(x + 3, y + 14, 14, 13);

  // Collar
  ctx.fillStyle = '#f0e8d0';
  ctx.fillRect(x + 8, y + 14, 4, 3);

  // Lapels
  ctx.fillStyle = '#a06030';
  ctx.fillRect(x + 6, y + 14, 3, 6);
  ctx.fillRect(x + 11, y + 14, 3, 6);

  // Neck
  ctx.fillStyle = '#c09060';
  ctx.fillRect(x + 8, y + 11, 4, 4);

  // Head
  ctx.fillStyle = '#c8a070';
  ctx.fillRect(x + 6, y + 4, 8, 8);

  // Hair
  ctx.fillStyle = '#2a1808';
  ctx.fillRect(x + 6, y + 4, 8, 2);

  // Eyes — serene, warm
  ctx.fillStyle = '#3a2010';
  ctx.fillRect(x + 7, y + 8, 2, 2);
  ctx.fillRect(x + 11, y + 8, 2, 2);

  // Serene smile
  ctx.fillStyle = '#8a5a30';
  ctx.fillRect(x + 7, y + 11, 6, 1);
  ctx.fillRect(x + 7, y + 12, 1, 1);
  ctx.fillRect(x + 12, y + 12, 1, 1);

  // Large book held in both hands in front
  ctx.fillStyle = '#1a3a6a';  // book cover (blue/deep)
  ctx.fillRect(x + 2, y + 20, 15, 12);
  ctx.fillStyle = '#0e2a50';  // book spine
  ctx.fillRect(x + 2, y + 20, 2, 12);
  ctx.fillStyle = '#f0e8d0';  // page edges
  ctx.fillRect(x + 17, y + 20, 1, 12);

  // Title text blocks on cover (representing "PATTERNS")
  ctx.fillStyle = '#fb923c';  // title in orange
  ctx.fillRect(x + 5, y + 23, 9, 2);  // title bar
  ctx.fillRect(x + 6, y + 26, 7, 1);  // subtitle line
  ctx.fillRect(x + 7, y + 28, 5, 1);

  // Decorative pattern symbol on book
  ctx.fillStyle = '#c8a020';
  ctx.fillRect(x + 8, y + 30, 3, 2); // diamond shape
  ctx.fillRect(x + 7, y + 31, 5, 1);

  // Hands holding book
  ctx.fillStyle = '#c8a070';
  ctx.fillRect(x + 2, y + 31, 3, 2);
  ctx.fillRect(x + 14, y + 31, 3, 2);

  // Arms
  ctx.fillStyle = '#c07840';
  ctx.fillRect(x + 1, y + 18, 3, 13);
  ctx.fillRect(x + 16, y + 18, 3, 13);
}

function drawSprite_jhaddu_C(ctx, cx, cy) {
  // Conference Speaker — at podium, laser pointer, audience suggested
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Audience seats (tiny dots behind/below speaker)
  ctx.fillStyle = '#2a2a4a';
  ctx.fillRect(x - 2, y + 34, 4, 3);
  ctx.fillRect(x + 4, y + 34, 4, 3);
  ctx.fillRect(x + 16, y + 34, 4, 3);
  ctx.fillRect(x - 2, y + 38, 3, 2);
  ctx.fillRect(x + 5, y + 38, 3, 2);
  ctx.fillRect(x + 17, y + 38, 3, 2);

  // Podium (trapezoid drawn as rects, wider at bottom)
  ctx.fillStyle = '#5a4a30';
  ctx.fillRect(x + 4, y + 22, 12, 3);   // top surface
  ctx.fillRect(x + 3, y + 25, 14, 2);   // upper body
  ctx.fillRect(x + 2, y + 27, 16, 3);   // lower body
  ctx.fillRect(x + 1, y + 30, 18, 4);   // base
  ctx.fillRect(x + 0, y + 34, 20, 3);   // foot

  // Podium front detail
  ctx.fillStyle = '#4a3a20';
  ctx.fillRect(x + 3, y + 26, 14, 1);

  // Notes on podium
  ctx.fillStyle = '#f0f0f0';
  ctx.fillRect(x + 6, y + 22, 8, 3);
  ctx.fillStyle = '#c0c0c0';
  ctx.fillRect(x + 7, y + 23, 6, 1);

  // Speaker body (standing behind podium, upper visible)
  // Suit
  ctx.fillStyle = '#2a2a38';
  ctx.fillRect(x + 4, y + 12, 12, 11);

  // Shirt
  ctx.fillStyle = '#f0f0f0';
  ctx.fillRect(x + 8, y + 12, 4, 4);

  // Tie (orange)
  ctx.fillStyle = '#fb923c';
  ctx.fillRect(x + 9, y + 12, 2, 6);

  // Neck
  ctx.fillStyle = '#c09060';
  ctx.fillRect(x + 8, y + 9, 4, 4);

  // Head
  ctx.fillStyle = '#c8a070';
  ctx.fillRect(x + 6, y + 2, 8, 8);

  // Hair
  ctx.fillStyle = '#2a1808';
  ctx.fillRect(x + 6, y + 2, 8, 2);

  // Eyes — engaged, looking out at audience
  ctx.fillStyle = '#3a2010';
  ctx.fillRect(x + 7, y + 6, 2, 2);
  ctx.fillRect(x + 11, y + 6, 2, 2);

  // Confident speaking mouth (slightly open)
  ctx.fillStyle = '#8a5a30';
  ctx.fillRect(x + 7, y + 9, 6, 1);
  ctx.fillStyle = '#4a2010';
  ctx.fillRect(x + 8, y + 10, 4, 1);

  // Left arm gripping podium sides
  ctx.fillStyle = '#2a2a38';
  ctx.fillRect(x + 3, y + 14, 3, 8);
  ctx.fillStyle = '#c8a070';
  ctx.fillRect(x + 3, y + 21, 3, 2);

  // Right arm extended with laser pointer
  ctx.fillStyle = '#2a2a38';
  ctx.fillRect(x + 14, y + 14, 3, 7);
  ctx.fillRect(x + 16, y + 18, 5, 2); // arm extending right
  ctx.fillStyle = '#c8a070';
  ctx.fillRect(x + 19, y + 18, 2, 2); // hand

  // Laser pointer (thin pen)
  ctx.fillStyle = '#c0c0c0';
  ctx.fillRect(x + 21, y + 18, 3, 1);
  // laser dot (red)
  ctx.fillStyle = '#ff2020';
  ctx.fillRect(x + 24, y + 17, 2, 2);
}

// ─── MORGAN (Morgan they/them) — #d946ef ────────────────────────────────────

function drawSprite_morgan_A(ctx, cx, cy) {
  // Wellness Coach — lavender cardigan, holding crystals, rainbow on chest
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Shoes (soft, rounded)
  ctx.fillStyle = '#b090c0';
  ctx.fillRect(x + 4, y + 36, 5, 4);
  ctx.fillRect(x + 11, y + 36, 5, 4);

  // Legs (soft lavender leggings)
  ctx.fillStyle = '#c4a8d8';
  ctx.fillRect(x + 5, y + 26, 4, 10);
  ctx.fillRect(x + 11, y + 26, 4, 10);

  // Cardigan body (soft lavender)
  ctx.fillStyle = '#c4a8d8';
  ctx.fillRect(x + 3, y + 14, 14, 13);

  // Cardigan texture (slightly lighter front panel)
  ctx.fillStyle = '#d4b8e8';
  ctx.fillRect(x + 7, y + 14, 6, 13);

  // Cardigan buttons (small)
  ctx.fillStyle = '#f0e8f8';
  ctx.fillRect(x + 9, y + 16, 2, 1);
  ctx.fillRect(x + 9, y + 19, 2, 1);
  ctx.fillRect(x + 9, y + 22, 2, 1);

  // Rainbow on chest (small arc)
  ctx.fillStyle = '#ef4444';
  ctx.fillRect(x + 4, y + 18, 6, 1);
  ctx.fillStyle = '#fb923c';
  ctx.fillRect(x + 4, y + 19, 5, 1);
  ctx.fillStyle = '#facc15';
  ctx.fillRect(x + 4, y + 20, 4, 1);
  ctx.fillStyle = '#4ade80';
  ctx.fillRect(x + 5, y + 21, 3, 1);
  ctx.fillStyle = '#60a5fa';
  ctx.fillRect(x + 5, y + 22, 3, 1);
  ctx.fillStyle = '#a78bfa';
  ctx.fillRect(x + 6, y + 23, 2, 1);

  // Neck
  ctx.fillStyle = '#d4a890';
  ctx.fillRect(x + 8, y + 11, 4, 4);

  // Head
  ctx.fillStyle = '#e0b898';
  ctx.fillRect(x + 6, y + 4, 8, 8);

  // Hair (soft, flowing — medium length)
  ctx.fillStyle = '#7a4a80';
  ctx.fillRect(x + 5, y + 4, 10, 2);
  ctx.fillRect(x + 5, y + 6, 2, 6);
  ctx.fillRect(x + 13, y + 6, 2, 6);
  ctx.fillRect(x + 5, y + 11, 1, 3);
  ctx.fillRect(x + 14, y + 11, 1, 3);

  // Eyes — gentle, warm
  ctx.fillStyle = '#5a3060';
  ctx.fillRect(x + 7, y + 8, 2, 2);
  ctx.fillRect(x + 11, y + 8, 2, 2);
  // sparkle
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(x + 8, y + 8, 1, 1);
  ctx.fillRect(x + 12, y + 8, 1, 1);

  // Gentle smile
  ctx.fillStyle = '#c07880';
  ctx.fillRect(x + 7, y + 11, 6, 1);
  ctx.fillRect(x + 7, y + 12, 1, 1);
  ctx.fillRect(x + 12, y + 12, 1, 1);

  // Left hand holding crystal cluster
  ctx.fillStyle = '#c4a8d8';
  ctx.fillRect(x + 0, y + 16, 3, 10);
  ctx.fillStyle = '#e0b898';
  ctx.fillRect(x + 0, y + 25, 3, 2);
  // crystals (purple/pink cluster)
  ctx.fillStyle = '#d946ef';
  ctx.fillRect(x - 2, y + 23, 3, 4);
  ctx.fillStyle = '#a020c0';
  ctx.fillRect(x - 1, y + 21, 2, 4);
  ctx.fillStyle = '#f0a0f8';
  ctx.fillRect(x + 0, y + 22, 2, 3);
  // crystal highlights
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(x - 1, y + 21, 1, 1);
  ctx.fillRect(x + 0, y + 22, 1, 1);

  // Right arm (at side)
  ctx.fillStyle = '#c4a8d8';
  ctx.fillRect(x + 17, y + 16, 3, 10);
  ctx.fillStyle = '#e0b898';
  ctx.fillRect(x + 17, y + 26, 3, 2);
}

function drawSprite_morgan_B(ctx, cx, cy) {
  // Reddit Therapist — computer with reddit alien, thoughtful expression, notebook
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Chair
  ctx.fillStyle = '#3a3050';
  ctx.fillRect(x + 2, y + 33, 2, 7);
  ctx.fillRect(x + 14, y + 33, 2, 7);
  ctx.fillRect(x + 1, y + 30, 16, 3);

  // Legs
  ctx.fillStyle = '#5a4060';
  ctx.fillRect(x + 5, y + 26, 4, 6);
  ctx.fillRect(x + 11, y + 26, 4, 6);

  // Body — soft purple sweater
  ctx.fillStyle = '#7a4a90';
  ctx.fillRect(x + 3, y + 15, 14, 12);

  // Collar
  ctx.fillStyle = '#e0d0f0';
  ctx.fillRect(x + 8, y + 15, 4, 3);

  // Neck
  ctx.fillStyle = '#d4a890';
  ctx.fillRect(x + 8, y + 12, 4, 4);

  // Head
  ctx.fillStyle = '#e0b898';
  ctx.fillRect(x + 6, y + 5, 8, 8);

  // Hair (loose, medium)
  ctx.fillStyle = '#7a4a80';
  ctx.fillRect(x + 5, y + 5, 10, 2);
  ctx.fillRect(x + 5, y + 7, 2, 5);
  ctx.fillRect(x + 13, y + 7, 2, 5);

  // Eyes — thoughtful (looking slightly to side)
  ctx.fillStyle = '#5a3060';
  ctx.fillRect(x + 7, y + 9, 2, 2);
  ctx.fillRect(x + 11, y + 9, 2, 2);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(x + 8, y + 9, 1, 1);
  ctx.fillRect(x + 12, y + 9, 1, 1);

  // Thoughtful neutral mouth
  ctx.fillStyle = '#c07880';
  ctx.fillRect(x + 8, y + 12, 4, 1);

  // Monitor/screen to the right
  ctx.fillStyle = '#2a2a3a';
  ctx.fillRect(x + 16, y + 12, 10, 8);  // screen body
  ctx.fillStyle = '#1a90ff';             // blue screen background
  ctx.fillRect(x + 17, y + 13, 8, 6);
  // Reddit alien head (small orange oval on screen)
  ctx.fillStyle = '#ff6314';
  ctx.fillRect(x + 18, y + 14, 4, 4);
  ctx.fillStyle = '#fff';
  ctx.fillRect(x + 19, y + 15, 1, 2);
  ctx.fillRect(x + 21, y + 15, 1, 2);
  // alien antennae
  ctx.fillStyle = '#ff6314';
  ctx.fillRect(x + 19, y + 13, 1, 2);
  ctx.fillRect(x + 22, y + 13, 1, 2);
  // monitor stand
  ctx.fillStyle = '#3a3a4a';
  ctx.fillRect(x + 20, y + 20, 2, 3);
  ctx.fillRect(x + 18, y + 22, 6, 2);

  // Notebook on lap (open)
  ctx.fillStyle = '#d4b896';
  ctx.fillRect(x + 4, y + 24, 10, 7);
  ctx.fillStyle = '#c8a870';
  ctx.fillRect(x + 4, y + 24, 2, 7); // binding
  ctx.fillStyle = '#b89870';
  ctx.fillRect(x + 7, y + 26, 6, 1);
  ctx.fillRect(x + 7, y + 28, 6, 1);

  // Arms holding notebook / pen
  ctx.fillStyle = '#7a4a90';
  ctx.fillRect(x + 1, y + 17, 3, 8);
  ctx.fillRect(x + 15, y + 17, 3, 8);
  ctx.fillStyle = '#d4a890';
  ctx.fillRect(x + 1, y + 25, 3, 2);
  ctx.fillRect(x + 15, y + 25, 3, 2);
  // pen in right hand
  ctx.fillStyle = '#8a6040';
  ctx.fillRect(x + 14, y + 24, 1, 4);
}

function drawSprite_morgan_C(ctx, cx, cy) {
  // Conflict-Averse — backing away, hands raised "let's calm down", soft colors
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Shoes (turned slightly — backing pose)
  ctx.fillStyle = '#b0a0c0';
  ctx.fillRect(x + 3, y + 36, 5, 4);
  ctx.fillRect(x + 10, y + 36, 4, 4);

  // Legs (slightly offset — backing)
  ctx.fillStyle = '#c8b8d8';
  ctx.fillRect(x + 4, y + 27, 4, 9);
  ctx.fillRect(x + 10, y + 28, 4, 8);

  // Body — soft pastel lilac
  ctx.fillStyle = '#d8c0e8';
  ctx.fillRect(x + 3, y + 15, 14, 13);

  // Collar
  ctx.fillStyle = '#f0e8f8';
  ctx.fillRect(x + 8, y + 15, 4, 3);

  // Neck (slightly turned — chin tucked)
  ctx.fillStyle = '#d4a890';
  ctx.fillRect(x + 8, y + 12, 4, 4);

  // Head (turned slightly away)
  ctx.fillStyle = '#e0b898';
  ctx.fillRect(x + 5, y + 5, 8, 8);

  // Hair
  ctx.fillStyle = '#7a4a80';
  ctx.fillRect(x + 4, y + 5, 10, 2);
  ctx.fillRect(x + 4, y + 7, 2, 6);
  ctx.fillRect(x + 12, y + 7, 2, 5);

  // Eyes — wide, slightly alarmed
  ctx.fillStyle = '#5a3060';
  ctx.fillRect(x + 6, y + 8, 3, 2);
  ctx.fillRect(x + 10, y + 8, 3, 2);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(x + 7, y + 8, 1, 1);
  ctx.fillRect(x + 11, y + 8, 1, 1);

  // Mouth — small "o" of concern
  ctx.fillStyle = '#c07880';
  ctx.fillRect(x + 7, y + 11, 4, 2);
  ctx.fillStyle = '#f0c0c0';
  ctx.fillRect(x + 8, y + 11, 2, 1);

  // Both arms raised in "please calm down" gesture
  // Left arm raised up and out
  ctx.fillStyle = '#d8c0e8';
  ctx.fillRect(x + 0, y + 15, 3, 5);   // upper arm
  ctx.fillRect(x - 2, y + 12, 3, 6);   // forearm raised
  ctx.fillStyle = '#d4a890';
  ctx.fillRect(x - 3, y + 10, 4, 3);   // hand open, palm out
  // palm detail lines
  ctx.fillStyle = '#c09070';
  ctx.fillRect(x - 3, y + 11, 4, 1);

  // Right arm raised up and out
  ctx.fillStyle = '#d8c0e8';
  ctx.fillRect(x + 17, y + 15, 3, 5);  // upper arm
  ctx.fillRect(x + 19, y + 12, 3, 6);  // forearm raised
  ctx.fillStyle = '#d4a890';
  ctx.fillRect(x + 19, y + 10, 4, 3);  // hand open, palm out
  ctx.fillStyle = '#c09070';
  ctx.fillRect(x + 19, y + 11, 4, 1);
}

// ─── THE-KID — #facc15 ───────────────────────────────────────────────────────

function drawSprite_the_kid_A(ctx, cx, cy) {
  // Speed Demon — running pose (leaning forward), blur lines, backwards cap, sneakers
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Motion blur lines (behind the figure)
  ctx.fillStyle = '#facc15';
  ctx.globalAlpha = 0.3;
  ctx.fillRect(x - 8, y + 16, 6, 1);
  ctx.fillRect(x - 10, y + 19, 8, 1);
  ctx.fillRect(x - 8, y + 22, 6, 1);
  ctx.fillRect(x - 6, y + 25, 5, 1);
  ctx.globalAlpha = 1.0;

  // Sneakers (mid-run)
  ctx.fillStyle = '#f0f0f0';
  ctx.fillRect(x + 12, y + 34, 6, 4);  // forward foot
  ctx.fillRect(x + 2, y + 36, 5, 3);   // back foot lifted
  // sneaker details
  ctx.fillStyle = '#facc15';
  ctx.fillRect(x + 13, y + 36, 4, 1);
  ctx.fillRect(x + 2, y + 37, 3, 1);

  // Legs — in running stride
  ctx.fillStyle = '#2a2a4a';  // dark shorts/tights
  ctx.fillRect(x + 11, y + 26, 4, 9);  // forward leg
  ctx.fillRect(x + 4, y + 24, 4, 8);   // back leg

  // Shorts
  ctx.fillStyle = '#facc15';
  ctx.fillRect(x + 4, y + 22, 12, 6);

  // Body — leaning forward ~15 degrees
  ctx.fillStyle = '#e07810';  // orange/warm shirt
  ctx.fillRect(x + 5, y + 13, 11, 11);

  // Leaning forward — chest out
  ctx.fillStyle = '#c05808';
  ctx.fillRect(x + 5, y + 13, 2, 5); // shading left edge

  // Neck
  ctx.fillStyle = '#e0b870';
  ctx.fillRect(x + 8, y + 10, 4, 4);

  // Head (slightly forward-tilted)
  ctx.fillStyle = '#f0c870';
  ctx.fillRect(x + 7, y + 4, 8, 7);

  // Backwards cap
  ctx.fillStyle = '#facc15';
  ctx.fillRect(x + 6, y + 4, 9, 2);   // cap body
  ctx.fillRect(x + 6, y + 6, 8, 1);   // brim hint
  ctx.fillRect(x + 5, y + 3, 3, 2);   // brim sticking backwards (left side)

  // Eyes — focused, squinting
  ctx.fillStyle = '#3a2010';
  ctx.fillRect(x + 8, y + 7, 2, 1);
  ctx.fillRect(x + 11, y + 7, 2, 1);

  // Grin — excited speed grin
  ctx.fillStyle = '#8a5020';
  ctx.fillRect(x + 8, y + 10, 5, 1);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(x + 9, y + 10, 3, 1);

  // Arms pumping
  ctx.fillStyle = '#e07810';
  ctx.fillRect(x + 2, y + 14, 3, 7);   // back arm (behind)
  ctx.fillRect(x + 16, y + 14, 3, 6);  // front arm (ahead)
  ctx.fillRect(x + 17, y + 19, 4, 3);  // forearm forward
  // Hands
  ctx.fillStyle = '#e0b870';
  ctx.fillRect(x + 1, y + 21, 3, 2);
  ctx.fillRect(x + 19, y + 21, 3, 2);
}

function drawSprite_the_kid_B(ctx, cx, cy) {
  // Racer — helmet, racing suit, crouched starting-block pose, checkerboard stripe
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Starting blocks (simple rects)
  ctx.fillStyle = '#4a4a5a';
  ctx.fillRect(x + 2, y + 32, 6, 3);
  ctx.fillRect(x + 10, y + 35, 8, 3);
  // block feet anchors
  ctx.fillStyle = '#3a3a4a';
  ctx.fillRect(x + 4, y + 35, 2, 5);
  ctx.fillRect(x + 8, y + 35, 2, 3);

  // Crouched legs (deep crouch/start pose)
  ctx.fillStyle = '#facc15';  // racing suit legs
  ctx.fillRect(x + 3, y + 25, 5, 8);  // back leg crouched
  ctx.fillRect(x + 11, y + 28, 6, 5); // front leg pushing

  // Racing shoes
  ctx.fillStyle = '#f0f0f0';
  ctx.fillRect(x + 3, y + 33, 5, 3);
  ctx.fillRect(x + 12, y + 33, 5, 3);
  ctx.fillStyle = '#facc15';
  ctx.fillRect(x + 4, y + 35, 3, 1);
  ctx.fillRect(x + 13, y + 35, 3, 1);

  // Racing suit body (yellow with checkerboard stripe)
  ctx.fillStyle = '#facc15';
  ctx.fillRect(x + 3, y + 14, 14, 12);

  // Checkerboard stripe across chest
  const stripeY = y + 18;
  for (let i = 0; i < 7; i++) {
    ctx.fillStyle = i % 2 === 0 ? '#1a1a1a' : '#facc15';
    ctx.fillRect(x + 3 + (i * 2), stripeY, 2, 3);
  }

  // Racing gloves (black)
  ctx.fillStyle = '#1a1a1a';
  ctx.fillRect(x + 0, y + 20, 3, 4);   // back hand on block
  ctx.fillRect(x + 17, y + 20, 3, 4);  // front hand on block

  // Arms reaching forward in start crouch
  ctx.fillStyle = '#facc15';
  ctx.fillRect(x + 0, y + 16, 3, 6);
  ctx.fillRect(x + 17, y + 16, 3, 6);

  // Neck
  ctx.fillStyle = '#e0b870';
  ctx.fillRect(x + 8, y + 11, 4, 4);

  // Racing helmet (full head coverage)
  ctx.fillStyle = '#facc15';
  ctx.fillRect(x + 5, y + 3, 10, 10);  // helmet main
  ctx.fillRect(x + 4, y + 5, 12, 7);   // helmet wide band

  // Helmet visor (dark tinted)
  ctx.fillStyle = '#1a1a2a';
  ctx.fillRect(x + 5, y + 7, 10, 4);
  ctx.fillStyle = '#3a3a5a';
  ctx.fillRect(x + 6, y + 7, 8, 2);    // visor glare

  // Helmet checkerboard stripe
  for (let i = 0; i < 5; i++) {
    ctx.fillStyle = i % 2 === 0 ? '#1a1a1a' : '#facc15';
    ctx.fillRect(x + 5 + (i * 2), y + 3, 2, 2);
  }

  // Helmet chin guard
  ctx.fillStyle = '#e0c000';
  ctx.fillRect(x + 6, y + 12, 8, 2);
}

function drawSprite_the_kid_C(ctx, cx, cy) {
  // Chaos Kid — wild hair everywhere, arms raised in excitement, big eyes, energy lines
  const x = Math.floor(cx - 10);
  const y = Math.floor(cy - 40);

  // Energy/excitement lines radiating out
  ctx.fillStyle = '#facc15';
  ctx.globalAlpha = 0.5;
  // radial burst lines
  ctx.fillRect(x - 4, y + 5, 3, 1);   // left
  ctx.fillRect(x + 21, y + 5, 3, 1);  // right
  ctx.fillRect(x + 8, y - 2, 1, 3);   // top center
  ctx.fillRect(x - 3, y + 12, 3, 1);
  ctx.fillRect(x + 20, y + 12, 3, 1);
  ctx.fillRect(x - 2, y + 2, 2, 1);
  ctx.fillRect(x + 20, y + 2, 2, 1);
  ctx.globalAlpha = 1.0;

  // Shoes
  ctx.fillStyle = '#f0f0f0';
  ctx.fillRect(x + 3, y + 36, 5, 4);
  ctx.fillRect(x + 12, y + 36, 5, 4);

  // Legs (springy stance — feet apart)
  ctx.fillStyle = '#3a3a5a';
  ctx.fillRect(x + 4, y + 28, 4, 8);
  ctx.fillRect(x + 12, y + 28, 4, 8);

  // Shorts
  ctx.fillStyle = '#facc15';
  ctx.fillRect(x + 3, y + 24, 14, 6);

  // Body — bright t-shirt
  ctx.fillStyle = '#f59e0b';
  ctx.fillRect(x + 4, y + 14, 12, 12);

  // Exclamation mark on shirt
  ctx.fillStyle = '#1a1a1a';
  ctx.fillRect(x + 9, y + 16, 2, 5);
  ctx.fillRect(x + 9, y + 22, 2, 2);

  // Neck
  ctx.fillStyle = '#f0c870';
  ctx.fillRect(x + 8, y + 11, 4, 4);

  // Head (round, energetic)
  ctx.fillStyle = '#fce0a0';
  ctx.fillRect(x + 5, y + 4, 10, 9);

  // Wild hair (spiky points in all directions)
  ctx.fillStyle = '#2a1808';
  // top spikes
  ctx.fillRect(x + 5, y + 2, 2, 3);
  ctx.fillRect(x + 8, y + 1, 2, 4);
  ctx.fillRect(x + 11, y + 0, 2, 5);
  ctx.fillRect(x + 13, y + 2, 2, 3);
  // side spikes
  ctx.fillRect(x + 3, y + 4, 3, 2);
  ctx.fillRect(x + 14, y + 4, 3, 2);
  ctx.fillRect(x + 2, y + 7, 3, 2);
  ctx.fillRect(x + 15, y + 6, 3, 2);
  // hair base
  ctx.fillRect(x + 5, y + 4, 10, 2);
  ctx.fillRect(x + 5, y + 6, 1, 3);
  ctx.fillRect(x + 14, y + 6, 1, 3);

  // BIG eyes (wide, excited circles)
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(x + 5, y + 7, 4, 4);
  ctx.fillRect(x + 11, y + 7, 4, 4);
  ctx.fillStyle = '#3a2010';
  ctx.fillRect(x + 6, y + 8, 2, 2);
  ctx.fillRect(x + 12, y + 8, 2, 2);
  // pupils
  ctx.fillStyle = '#1a0808';
  ctx.fillRect(x + 7, y + 8, 1, 1);
  ctx.fillRect(x + 13, y + 8, 1, 1);
  // eye shines
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(x + 6, y + 7, 1, 1);
  ctx.fillRect(x + 12, y + 7, 1, 1);

  // Big excited open mouth / grin
  ctx.fillStyle = '#3a1808';
  ctx.fillRect(x + 6, y + 11, 8, 2);
  ctx.fillStyle = '#f0a0a0';
  ctx.fillRect(x + 7, y + 11, 6, 2);
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(x + 7, y + 11, 2, 1);
  ctx.fillRect(x + 11, y + 11, 2, 1);

  // Both arms raised high in excitement
  // Left arm
  ctx.fillStyle = '#f59e0b';
  ctx.fillRect(x + 1, y + 15, 3, 6);   // upper arm
  ctx.fillRect(x - 2, y + 9, 3, 8);    // forearm raised
  ctx.fillStyle = '#f0c870';
  ctx.fillRect(x - 3, y + 7, 4, 3);   // hand

  // Right arm
  ctx.fillStyle = '#f59e0b';
  ctx.fillRect(x + 16, y + 15, 3, 6);  // upper arm
  ctx.fillRect(x + 19, y + 9, 3, 8);   // forearm raised
  ctx.fillStyle = '#f0c870';
  ctx.fillRect(x + 19, y + 7, 4, 3);   // hand

  // Extra energy sparks
  ctx.fillStyle = '#fffb70';
  ctx.fillRect(x - 4, y + 8, 1, 1);
  ctx.fillRect(x + 23, y + 8, 1, 1);
  ctx.fillRect(x + 10, y - 2, 1, 1);
}
