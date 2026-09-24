---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
tags: [trigger, root-cause-analysis]
---

Production is throwing "Cannot read properties of undefined (reading 'id')" in
the checkout flow whenever a guest (not-logged-in) user checks out. It works
fine for logged-in users. Started after yesterday's deploy. Here's the stack
trace: at CheckoutService.finalize (checkout.ts:42) -> at
CartController.submit (cart.ts:88).
