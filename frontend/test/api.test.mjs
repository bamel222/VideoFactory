import { test } from "node:test";
import assert from "node:assert";

import { can } from "../src/lib/api.js";

// can() reads from localStorage via getRole(); stub it
function withRole(role, fn) {
  const store = global.window;
  global.window = {
    localStorage: {
      getItem: (k) => (k === "vf_role" ? role : null),
    },
  };
  try {
    fn();
  } finally {
    if (store) global.window = store;
    else delete global.window;
  }
}

test("owner can publish and manage users", () => {
  withRole("owner", () => {
    assert.equal(can("publication.final"), true);
    assert.equal(can("users.manage"), true);
    assert.equal(can("billing.manage"), true);
  });
});

test("admin cannot publish nor manage users", () => {
  withRole("admin", () => {
    assert.equal(can("publication.final"), false);
    assert.equal(can("users.manage"), false);
    assert.equal(can("review.operational"), true);
    assert.equal(can("pipeline.run"), true);
  });
});

test("reviewer is read-only", () => {
  withRole("reviewer", () => {
    assert.equal(can("review.quality"), true);
    assert.equal(can("pipeline.run"), false);
    assert.equal(can("providers.manage"), false);
  });
});
