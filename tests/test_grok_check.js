const assert = require("assert");
const path = require("path");
const game = require(path.join(__dirname, "..", "grok-check", "logic.js"));

function pick(map) {
  return Object.keys(map).map(function (scenarioId) {
    return { scenarioId: scenarioId, choiceId: map[scenarioId] };
  });
}

function verdictId(map) {
  return game.play(pick(map)).verdict.id;
}

assert.strictEqual(game.scenarios.length, 7, "seven scenes");

game.scenarios.forEach(function (scenario) {
  assert.ok(scenario.choices.length >= 3, scenario.id + " has choices");
  scenario.choices.forEach(function (choice) {
    ["learn", "copy", "verify", "integrity", "first"].forEach(function (key) {
      assert.strictEqual(typeof choice.scores[key], "number", key);
    });
  });
});

assert.strictEqual(
  verdictId({
    deadline: "hint",
    concept: "tutor",
    mismatch: "show-work",
    policy: "honor",
    essay: "talk-then-write",
    grade: "board",
    friend: "learn-not-skip",
  }),
  "yes-tutor"
);

assert.strictEqual(
  verdictId({
    deadline: "turn-in",
    concept: "notes-first",
    mismatch: "show-work",
    policy: "ask-teacher",
    essay: "draft-first",
    grade: "check",
    friend: "refuse",
  }),
  "optional"
);

assert.strictEqual(
  verdictId({
    deadline: "paste",
    concept: "answers-only",
    mismatch: "trust",
    policy: "honor",
    essay: "ghostwrite",
    grade: "couldnt",
    friend: "follow",
  }),
  "not-yet"
);

assert.strictEqual(
  verdictId({
    deadline: "paste",
    concept: "answers-only",
    mismatch: "trust",
    policy: "secret",
    essay: "ghostwrite",
    grade: "freeze",
    friend: "share",
  }),
  "no-sneak"
);

assert.strictEqual(
  verdictId({
    deadline: "copy-read",
    concept: "tutor",
    mismatch: "book-only",
    policy: "honor",
    essay: "stitch",
    grade: "board",
    friend: "learn-not-skip",
  }),
  "yes-rules"
);

const scored = game.scoreAnswers(
  pick({
    deadline: "hint",
    concept: "tutor",
    mismatch: "show-work",
    policy: "honor",
    essay: "talk-then-write",
    grade: "board",
    friend: "learn-not-skip",
  })
);
assert.ok(scored.learn >= 8, "tutor path learns");
assert.ok(scored.copy <= 3, "tutor path does not copy much");

const fs = require("fs");
const html = fs.readFileSync(
  path.join(__dirname, "..", "grok-check", "index.html"),
  "utf8"
);
assert.ok(html.includes('id="app"'));
assert.ok(html.includes("logic.js"));
assert.ok(html.includes("app.js"));

console.log("OK: Grok Compass scoring paths pass");
