import { Router } from "./router.js";

async function main() {
  const router = Router.init();
  const short = await router.generateText({
    prompt: "What is 2+2?",
    max_tokens: 64,
  });
  console.log("SHORT:", short.routing.target, short.routing.reason);

  const long = await router.generateText({
    prompt: "x".repeat(600),
    max_tokens: 64,
  });
  console.log("LONG:", long.routing.target, long.routing.reason);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
