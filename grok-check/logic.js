/**
 * Grok Compass scoring. No DOM — safe to load in Node tests.
 */
(function (root) {
  const scenarios = [
    {
      id: "deadline",
      title: "The 20-minute crunch",
      prompt:
        "It's 9:40. Homework is due at 10:00. You're stuck on problem 4.",
      choices: [
        {
          id: "paste",
          label: "Paste the whole worksheet into Grok and turn in whatever it writes.",
          scores: { learn: 0, copy: 3, verify: 0, integrity: -1, first: 0 },
        },
        {
          id: "hint",
          label: "Ask Grok for a hint on problem 4, then finish the rest yourself.",
          scores: { learn: 2, copy: 0, verify: 1, integrity: 1, first: 1 },
        },
        {
          id: "turn-in",
          label: "Turn in what you have and ask the teacher tomorrow.",
          scores: { learn: 1, copy: 0, verify: 0, integrity: 2, first: 2 },
        },
        {
          id: "copy-read",
          label: "Get the answer from Grok, copy it, and skim the steps so you \"kind of\" get it.",
          scores: { learn: 0, copy: 2, verify: 0, integrity: 0, first: 0 },
        },
      ],
    },
    {
      id: "concept",
      title: "The confusing idea",
      prompt:
        "You don't actually understand the idea behind tonight's work. A friend says Grok can explain anything.",
      choices: [
        {
          id: "tutor",
          label: "Ask Grok to explain it simply, then try a practice problem without looking.",
          scores: { learn: 3, copy: 0, verify: 1, integrity: 1, first: 1 },
        },
        {
          id: "answers-only",
          label: "Skip the explanation. Just get tonight's answers.",
          scores: { learn: 0, copy: 3, verify: 0, integrity: -1, first: 0 },
        },
        {
          id: "notes-first",
          label: "Read your notes first. Ask Grok only about the part that still doesn't click.",
          scores: { learn: 2, copy: 0, verify: 1, integrity: 1, first: 3 },
        },
        {
          id: "fake-it",
          label: "Skip it. You'll fake it in class.",
          scores: { learn: -1, copy: 1, verify: 0, integrity: 0, first: 0 },
        },
      ],
    },
    {
      id: "mismatch",
      title: "The confident wrong answer",
      prompt:
        "Grok's answer doesn't match the example in the textbook. Grok sounds sure of itself.",
      choices: [
        {
          id: "trust",
          label: "Trust Grok. It sounds more sure than the book.",
          scores: { learn: 0, copy: 1, verify: -2, integrity: 0, first: 0 },
        },
        {
          id: "show-work",
          label: "Ask Grok to show the steps, then check them against the book.",
          scores: { learn: 2, copy: 0, verify: 3, integrity: 1, first: 1 },
        },
        {
          id: "guess",
          label: "Throw both out and guess.",
          scores: { learn: 0, copy: 0, verify: -1, integrity: 0, first: 0 },
        },
        {
          id: "book-only",
          label: "Copy the textbook method even if you don't know why it works.",
          scores: { learn: 0, copy: 1, verify: 1, integrity: 1, first: 0 },
        },
      ],
    },
    {
      id: "policy",
      title: "The classroom rule",
      prompt: 'The teacher said: "No AI on this assignment."',
      choices: [
        {
          id: "honor",
          label: "Don't use Grok on it. You can study with it after it's turned in.",
          scores: { learn: 1, copy: 0, verify: 0, integrity: 3, first: 2 },
        },
        {
          id: "secret",
          label: "Use it anyway. Nobody will know.",
          scores: { learn: 0, copy: 2, verify: 0, integrity: -3, first: 0 },
        },
        {
          id: "rewrite",
          label: "Use it for the work, then rewrite so it doesn't look like AI.",
          scores: { learn: 0, copy: 2, verify: 0, integrity: -2, first: 0 },
        },
        {
          id: "ask-teacher",
          label: "Ask the teacher what kind of help is allowed.",
          scores: { learn: 1, copy: 0, verify: 0, integrity: 3, first: 1 },
        },
      ],
    },
    {
      id: "essay",
      title: "The two-page essay",
      prompt: "You have a two-page essay due Friday. The blank page is loud.",
      choices: [
        {
          id: "ghostwrite",
          label: "Let Grok write it. Change a few words so it sounds like you.",
          scores: { learn: 0, copy: 3, verify: 0, integrity: -2, first: 0 },
        },
        {
          id: "talk-then-write",
          label: "Talk through your idea with Grok, then write every sentence yourself.",
          scores: { learn: 3, copy: 0, verify: 1, integrity: 2, first: 1 },
        },
        {
          id: "draft-first",
          label: "Write a messy draft first. Ask Grok what is unclear.",
          scores: { learn: 2, copy: 0, verify: 1, integrity: 2, first: 3 },
        },
        {
          id: "stitch",
          label: "Make an outline together, let Grok write the paragraphs, and stitch them.",
          scores: { learn: 1, copy: 2, verify: 0, integrity: -1, first: 0 },
        },
      ],
    },
    {
      id: "grade",
      title: "The A",
      prompt: "You got an A. You used Grok a lot. Be honest with yourself:",
      choices: [
        {
          id: "couldnt",
          label: "I couldn't have done it without Grok doing the work.",
          scores: { learn: -1, copy: 2, verify: 0, integrity: 0, first: 0 },
        },
        {
          id: "board",
          label: "I could explain every part on the board if the teacher asked.",
          scores: { learn: 3, copy: 0, verify: 2, integrity: 1, first: 1 },
        },
        {
          id: "freeze",
          label: "I'd freeze if I had to do it again without Grok.",
          scores: { learn: 0, copy: 2, verify: -1, integrity: 0, first: 0 },
        },
        {
          id: "check",
          label: "I used it to check my work after I finished.",
          scores: { learn: 2, copy: 0, verify: 3, integrity: 2, first: 3 },
        },
      ],
    },
    {
      id: "friend",
      title: "Everyone does it",
      prompt: 'A friend says: "Just get Grok to do it. Everyone does."',
      choices: [
        {
          id: "follow",
          label: "Do it their way. You don't want to be the only one working.",
          scores: { learn: 0, copy: 2, verify: 0, integrity: -1, first: 0 },
        },
        {
          id: "learn-not-skip",
          label: "Use it to learn, not to skip. Tell your friend that's the deal.",
          scores: { learn: 2, copy: 0, verify: 1, integrity: 2, first: 1 },
        },
        {
          id: "refuse",
          label: "Don't use it for this. You'll do the work.",
          scores: { learn: 1, copy: 0, verify: 0, integrity: 2, first: 3 },
        },
        {
          id: "share",
          label: "Use it, then share the answers with your friend.",
          scores: { learn: 0, copy: 3, verify: 0, integrity: -3, first: 0 },
        },
      ],
    },
  ];

  const emptyScores = function () {
    return { learn: 0, copy: 0, verify: 0, integrity: 0, first: 0 };
  };

  function findChoice(scenarioId, choiceId) {
    const scenario = scenarios.find(function (item) {
      return item.id === scenarioId;
    });
    if (!scenario) {
      throw new Error("Unknown scenario: " + scenarioId);
    }
    const choice = scenario.choices.find(function (item) {
      return item.id === choiceId;
    });
    if (!choice) {
      throw new Error("Unknown choice: " + scenarioId + "/" + choiceId);
    }
    return choice;
  }

  function addScores(total, delta) {
    total.learn += delta.learn;
    total.copy += delta.copy;
    total.verify += delta.verify;
    total.integrity += delta.integrity;
    total.first += delta.first;
    return total;
  }

  function scoreAnswers(answers) {
    const total = emptyScores();
    answers.forEach(function (answer) {
      const choice = findChoice(answer.scenarioId, answer.choiceId);
      addScores(total, choice.scores);
    });
    return total;
  }

  const verdicts = {
    "yes-tutor": {
      id: "yes-tutor",
      headline: "Yes — as a tutor, not a ghostwriter",
      tone: "go",
      student:
        "You already try, check your work, and care about understanding. Grok can be a patient study partner: hints, explanations, and extra practice. Keep writing the sentences and solving the problems yourself.",
      adult:
        "This student is a good fit. Suggest Grok for explanations and practice, not finished assignments. A simple rule: they should be able to redo the work on a blank page afterward.",
    },
    "yes-rules": {
      id: "yes-rules",
      headline: "Yes, with ground rules",
      tone: "caution",
      student:
        "Grok could help you, but only if you use it like a coach. Try first. Ask for hints, not answers. If you cannot explain it, you did not finish yet.",
      adult:
        "They may benefit, but they will drift toward shortcuts without rules. Agree on: no secret use, no pasting whole assignments, and they must show their own steps. Sit with them for the first few sessions.",
    },
    optional: {
      id: "optional",
      headline: "They don't need it — it is optional",
      tone: "optional",
      student:
        "You already try on your own and keep your work honest. Grok is not required. If you use it, treat it as a second opinion after you have attempted the problem.",
      adult:
        "This student is fairly independent. Grok is a nice extra, not a need. Do not push it. If they want it, use it for checking and deeper questions after they attempt the work.",
    },
    "not-yet": {
      id: "not-yet",
      headline: "Not yet — too easy to skip the thinking",
      tone: "wait",
      student:
        "Right now Grok would mostly do the assignment for you. That feels like relief tonight and confusion on the test. Build the habit of trying first. Come back to Grok when you want explanations, not escape.",
      adult:
        "Hold off. This pattern is homework-machine use. Work on attempt-first habits, notes, and asking a person for a hint. Revisit Grok later with you in the room.",
    },
    "no-sneak": {
      id: "no-sneak",
      headline: "No — honesty first",
      tone: "stop",
      student:
        "The choices leaned toward hiding the help or handing the work to someone else. That is not a Grok problem yet. It is a trust problem. Tools can wait until using them in the open feels normal.",
      adult:
        "Do not introduce Grok until the honesty question is settled. Talk about class rules, why secret use backfires, and how to ask for legitimate help. Grok would make the wrong habit easier.",
    },
  };

  function recommend(scores) {
    if (scores.integrity <= -3) {
      return verdicts["no-sneak"];
    }
    if (scores.copy >= 6 && scores.learn <= 4) {
      return verdicts["not-yet"];
    }
    if (scores.learn >= 12 && scores.integrity >= 4 && scores.copy <= 3) {
      return verdicts["yes-tutor"];
    }
    if (scores.first >= 12 && scores.copy <= 2 && scores.integrity >= 6) {
      return verdicts.optional;
    }
    return verdicts["yes-rules"];
  }

  function play(answers) {
    const scores = scoreAnswers(answers);
    const verdict = recommend(scores);
    return { scores: scores, verdict: verdict };
  }

  const api = {
    scenarios: scenarios,
    emptyScores: emptyScores,
    scoreAnswers: scoreAnswers,
    recommend: recommend,
    play: play,
    verdicts: verdicts,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.GrokCheck = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
