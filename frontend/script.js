const form = document.getElementById("recommendation-form");
const messageInput = document.getElementById("message");
const submitButton = document.getElementById("submit-button");
const resetButton = document.getElementById("reset-button");
const buttonLabel = document.getElementById("button-label");
const spinner = document.getElementById("spinner");
const statusBox = document.getElementById("status");
const clarification = document.getElementById("clarification");
const recommendations = document.getElementById("recommendations");
const results = document.getElementById("results");
const conditionsBox = document.getElementById("conditions");
const notes = document.getElementById("notes");
const exampleButtons = [...document.querySelectorAll(".example")];

let conversationHistory = [];
let lastQuestions = [];
let requestInProgress = false;

const examples = {
    tomato:
        "I want tomatoes for warm weather, with a published maturity " +
        "within 60 days after transplanting. My budget is 3 USD per packet.",

    lettuce:
        "I want lettuce for cool weather, with a published maturity " +
        "within 60 days from sowing. My budget is 3 USD per packet.",

    carrot:
        "I want carrots for clay soil. My budget is 3 USD per packet.",
};

function addText(parent, tag, value, className = "") {
    const element = document.createElement(tag);
    element.textContent = value;

    if (className) {
        element.className = className;
    }

    parent.appendChild(element);
    return element;
}

function setStatus(text, isError = false) {
    statusBox.textContent = text;
    statusBox.className = isError ? "status error" : "status";
}

function setBusy(busy) {
    submitButton.disabled = busy;
    resetButton.disabled = busy;
    messageInput.disabled = busy;

    exampleButtons.forEach(button => {
        button.disabled = busy;
    });

    spinner.hidden = !busy;
    buttonLabel.textContent = busy
        ? "Finding your options…"
        : "Find seed options";

    form.setAttribute("aria-busy", String(busy));
}

function clearResults() {
    results.replaceChildren();
    conditionsBox.replaceChildren();
    clarification.replaceChildren();
    notes.replaceChildren();

    recommendations.hidden = true;
    clarification.hidden = true;
    notes.hidden = true;
}

function resetConversation() {
    conversationHistory = [];
    lastQuestions = [];
}

exampleButtons.forEach(button => {
    button.addEventListener("click", () => {
        if (requestInProgress) return;

        resetConversation();
        clearResults();
        setStatus("");

        messageInput.value = examples[button.dataset.example] || "";
        messageInput.focus();
    });
});

resetButton.addEventListener("click", () => {
    if (requestInProgress) return;

    form.reset();
    resetConversation();
    clearResults();
    setStatus("");
    messageInput.focus();
});

function showNotes(items) {
    const unique = [
        ...new Set(
            items.filter(
                item => typeof item === "string" && item.trim()
            )
        ),
    ];

    if (!unique.length) return;

    notes.hidden = false;
    addText(notes, "h2", "Before you choose");

    const list = document.createElement("ul");

    unique.forEach(item => {
        addText(list, "li", item);
    });

    notes.appendChild(list);
}

function showConditions(conditions) {
    const labels = [
        conditions.crop_type,
        conditions.season,
    ];

    if (conditions.max_maturity_days != null) {
        labels.push(
            `Published maturity: up to ${conditions.max_maturity_days} days`
        );
    }

    if (conditions.budget_amount != null) {
        labels.push(
            [
                "Budget:",
                conditions.budget_amount,
                conditions.budget_currency || "",
                conditions.budget_basis || "",
            ]
                .filter(value => value !== "")
                .join(" ")
        );
    }

    labels.filter(Boolean).forEach(label => {
        addText(conditionsBox, "span", label, "condition");
    });
}

function addFact(parent, label, value, detail = "") {
    const fact = document.createElement("div");
    fact.className = "fact";

    addText(fact, "span", label, "fact-label");
    addText(fact, "span", value, "fact-value");

    if (detail) {
        addText(fact, "span", detail, "fact-detail");
    }

    parent.appendChild(fact);
}

function renderProduct(product, explanation) {
    const card = document.createElement("article");
    card.className = "card";

    addText(card, "div", "Catalogue match", "match-label");

    const fullName = product.product_name || "Seed product";
    const nameParts = fullName.match(/^(\d+)\s*-\s*(.+)$/);

    addText(card, "h3", nameParts ? nameParts[2] : fullName);

    if (nameParts) {
        addText(
            card,
            "p",
            `Product code: ${nameParts[1]}`,
            "product-id"
        );
    }

    addText(
        card,
        "div",
        [product.crop_type, product.suitable_season]
            .filter(Boolean)
            .join(" · "),
        "crop-season"
    );

    const facts = document.createElement("div");
    facts.className = "facts";

    const numericPrice = Number(product.price_usd_per_packet);
    const priceKnown =
        product.price_usd_per_packet != null &&
        product.price_usd_per_packet !== "" &&
        Number.isFinite(numericPrice);

    addFact(
        facts,
        "Wholesale unit quote",
        priceKnown
            ? `$${numericPrice.toFixed(2)} USD per packet`
            : "Not specified",
        "Order conditions apply"
    );

    let maturityDetail = "Starting point may be unspecified";

    if (["Tomato", "Eggplant"].includes(product.crop_type)) {
        maturityDetail = "Counted after transplanting";
    } else if (product.crop_type === "Lettuce") {
        maturityDetail = "Counted from direct seeding";
    }

    const maturity = product.maturity_period_days;
    const maturityKnown =
        maturity != null &&
        maturity !== "" &&
        maturity !== "Not specified";

    addFact(
        facts,
        "Published maturity estimate",
        maturityKnown ? `${maturity} days` : "Not specified",
        maturityKnown ? maturityDetail : ""
    );

    card.appendChild(facts);

    addText(
        card,
        "p",
        explanation ||
            "A simple explanation is unavailable. " +
            "You can still review the catalogue details.",
        "explanation"
    );

    if (
        (product.product_description || "")
            .toLowerCase()
            .includes("supplier variant was unavailable")
    ) {
        addText(
            card,
            "p",
            "This supplier variant was unavailable " +
            "when the catalogue was checked.",
            "availability"
        );
    }

    const details = document.createElement("details");

    addText(
        details,
        "summary",
        "View soil and water guidance"
    );

    const soil = product.soil_type || "Not specified";
    const soilParagraph = document.createElement("p");

    addText(
        soilParagraph,
        "strong",
        soil.startsWith("Crop guidance:")
            ? "General crop soil guidance"
            : "Supplier soil guidance"
    );

    addText(
        soilParagraph,
        "span",
        soil.replace(/^Crop guidance:\s*/, "")
    );

    details.appendChild(soilParagraph);

    const waterParagraph = document.createElement("p");

    addText(
        waterParagraph,
        "strong",
        "General crop water guidance"
    );

    addText(
        waterParagraph,
        "span",
        (product.water_requirement || "Not specified")
            .replace(/^Crop guidance:\s*/, "")
    );

    details.appendChild(waterParagraph);
    card.appendChild(details);
    results.appendChild(card);
}

function showFollowUp(questions, previousReply = "") {
    clarification.replaceChildren();
    clarification.hidden = false;

    addText(
        clarification,
        "h2",
        "A little more information"
    );

    const list = document.createElement("ul");

    questions.forEach(question => {
        addText(list, "li", question);
    });

    clarification.appendChild(list);

    addText(
        clarification,
        "p",
        "Reply below. We’ll keep the details you already provided."
    );

    const replyForm = document.createElement("form");
    replyForm.className = "follow-up-form";

    const label = addText(replyForm, "label", "Your answer");
    label.htmlFor = "follow-up-answer";

    const input = document.createElement("input");
    input.id = "follow-up-answer";
    input.className = "follow-up-input";
    input.type = "text";
    input.required = true;
    input.maxLength = 2000;
    input.placeholder = "For example: Tomato, or USD per packet";
    input.value = previousReply;

    replyForm.appendChild(input);

    const actions = document.createElement("div");
    actions.className = "actions";

    const button = addText(
        actions,
        "button",
        "Continue",
        "primary"
    );

    button.type = "submit";

    replyForm.appendChild(actions);
    clarification.appendChild(replyForm);

    replyForm.addEventListener("submit", event => {
        event.preventDefault();

        if (requestInProgress) return;

        const answer = input.value.trim();

        if (!answer) {
            setStatus("Please enter your answer.", true);
            input.focus();
            return;
        }

        requestSeeds(answer, true);
    });

    input.focus();
}

async function requestSeeds(message, isFollowUp = false) {
    if (requestInProgress) return;

    if (isFollowUp && conversationHistory.length >= 12) {
        setStatus(
            "Please start again and include your details in one message.",
            true
        );
        return;
    }

    const history = isFollowUp
        ? conversationHistory.map(item => ({ ...item }))
        : [];

    const questionsBeforeRequest = [...lastQuestions];

    requestInProgress = true;
    clearResults();
    setBusy(true);

    setStatus(
        "Checking the catalogue and preparing simple explanations. " +
        "This may take a little time."
    );

    try {
        const response = await fetch("/recommend", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                message,
                history,
            }),
        });

        let data;

        try {
            data = await response.json();
        } catch {
            throw new Error(
                "The server returned an unexpected response. " +
                "Please try again."
            );
        }

        if (!response.ok) {
            throw new Error(
                typeof data.detail === "string"
                    ? data.detail
                    : "We couldn’t complete your request. " +
                      "Please try again."
            );
        }

        const supportedStatuses = [
            "needs_clarification",
            "no_matches",
            "unsupported_requirements",
            "success",
        ];

        if (!supportedStatuses.includes(data.status)) {
            throw new Error(
                "An unexpected response was received. Please try again."
            );
        }

        if (
            data.status === "success" &&
            !Array.isArray(data.products)
        ) {
            throw new Error(
                "The product response was incomplete. Please try again."
            );
        }

        const updatedHistory = [
            ...history,
            {
                role: "user",
                content: message,
            },
        ];

        if (data.status === "needs_clarification") {
            const questions = Array.isArray(data.questions)
                ? data.questions.filter(
                    question =>
                        typeof question === "string" &&
                        question.trim()
                )
                : [];

            if (!questions.length) {
                throw new Error(
                    "The clarification response was incomplete. " +
                    "Please try again."
                );
            }

            updatedHistory.push({
                role: "assistant",
                content: questions.join("\n").slice(0, 2000),
            });

            conversationHistory = updatedHistory;
            lastQuestions = questions;

            setStatus("Please answer the question below.");
            showFollowUp(questions);
            return;
        }

        conversationHistory = updatedHistory;
        lastQuestions = [];

        if (data.status === "no_matches") {
            setStatus(
                "No catalogue products meet those filters. " +
                "Update your message with a different crop, " +
                "a longer maturity limit, or a different budget."
            );

            showNotes(data.warnings || []);
            return;
        }

        if (data.status === "unsupported_requirements") {
            setStatus(
                "We can’t check every condition in your message yet."
            );

            showNotes(data.warnings || []);
            return;
        }

        recommendations.hidden = false;
        setStatus("Your catalogue matches are ready.");

        document.getElementById("results-description").textContent =
            `${data.products.length} options match the filters ` +
            "checked by this system.";

        showConditions(data.conditions || {});

        const explanations = new Map(
            (data.explanation?.products || []).map(product => [
                product.product_name,
                product.explanation,
            ])
        );

        data.products.forEach(product => {
            renderProduct(
                product,
                explanations.get(product.product_name)
            );
        });

        showNotes([
            "The listed prices are wholesale unit quotes for " +
            "Guaranteed Sale Tier 1 orders of 150–399 total packets. " +
            "They are not single-packet retail prices.",
            ...(data.warnings || []),
            ...(data.explanation?.limitations || []),
        ]);
    } catch (error) {
        if (isFollowUp && questionsBeforeRequest.length) {
            showFollowUp(questionsBeforeRequest, message);
        }

        setStatus(
            error instanceof TypeError
                ? "We couldn’t connect. Check that your backend " +
                  "is running, then try again."
                : error.message ||
                  "Something went wrong. Please try again.",
            true
        );
    } finally {
        requestInProgress = false;
        setBusy(false);
    }
}

form.addEventListener("submit", event => {
    event.preventDefault();

    if (requestInProgress) return;

    const message = messageInput.value.trim();

    if (!message) {
        setStatus(
            "Please tell us what you would like to grow.",
            true
        );

        messageInput.focus();
        return;
    }

    resetConversation();
    requestSeeds(message);
});