# Smart Secret Santa

**Less guessing. More thoughtful gifting.**

Smart Secret Santa is a responsive website designed to make Secret Santa gifting more personal. Most Secret Santa tools stop after randomly assigning participants. Smart Secret Santa goes further by using each participant's interests, preferences and wishlist to help their assigned Santa choose a gift the recipient will genuinely appreciate.

The core idea is simple: **help people give better gifts, not just assign people to each other.**

> **Project status:** Early MVP. The project was started as a React website and later paused because Secret Santa is seasonal. The current repository contains an initial frontend scaffold. This README describes the intended product and decisions to guide development; it should not be read as a claim that every listed feature is already implemented.

---

## 1. Product at a glance

A group organizer creates a Secret Santa group and shares it with participants. Each participant joins, completes a short questionnaire and creates a wishlist. Once the group closes, the system assigns everyone one recipient. Each participant then gets a private Gifter experience with information about their assigned recipient, including relevant questionnaire insights, wishlist items, AI-assisted gift recommendations and the recipient's delivery address.

### The intended flow

1. An organizer creates a group and sets its name and maximum gift budget.
2. The system generates a unique six-digit group passkey.
3. Participants join using an invitation link or the passkey.
4. Each participant provides their details, completes a questionnaire and builds a wishlist.
5. After the three-day joining window, the group locks and assignments are generated automatically.
6. Each participant receives an assignment notification and opens their private Gifter screen.
7. The assigned Santa uses the recipient information, wishlist and recommendations to choose and deliver a thoughtful gift.

Christmas Secret Santa is the initial use case. Birthdays, anniversaries, office gifting and other occasions may be considered later, but they are not part of the initial MVP scope.

## 2. Product positioning and principles

Smart Secret Santa should not be positioned as just another random assignment tool. Random assignment is a commodity feature. The differentiator is helping people discover gifts their recipients are more likely to appreciate and use.

The experience should feel:

- Personal and thoughtful.
- Fun and simple.
- Trustworthy, particularly when handling assignments and delivery details.
- Lightweight, not like a complicated corporate event-management tool.

The product should avoid unnecessary complexity. Prioritize a useful, secure MVP over features that do not improve the core gifting experience.

## 3. User roles

There are two primary roles.

### Organizer

The organizer creates and manages the group. They can:

- Set the group name and maximum gift budget.
- Provide their own name and email.
- Receive a unique six-digit group passkey.
- Share the passkey or invitation links with participants.
- Monitor who has joined.
- Manage participants during the initial three-day joining window.
- Resend invitations and access links.
- Switch between Organizer mode and their own Gifter mode.

**The organizer is also a participant.** They must complete the participant flow and receive one recipient assignment like everyone else.

The organizer must not automatically be able to see everyone else's assignments. Assignment privacy applies to the organizer too.

### Gifter / participant

Every participant, including the organizer:

- Joins a group.
- Provides their name and email.
- Completes the questionnaire.
- Provides a delivery address.
- Creates or edits a wishlist.
- Receives exactly one assigned recipient.
- Views that recipient's relevant details, wishlist and recommendations.
- Uses the available information to choose and deliver a gift.

There is no separate recipient-facing experience in the MVP. Every participant is both a recipient, whose information helps someone else choose a gift, and a gifter, who buys for their assigned person.

## 4. Creating and joining a group

### Creating a group

The organizer provides:

- Group name.
- Maximum gift budget.
- Organizer name.
- Organizer email.

The system generates a unique six-digit passkey for the group. The organizer shares this passkey with participants.

### Joining an existing group

There are two supported entry paths.

**Option A: Invitation link**

The organizer sends a personalized invitation email containing a deep link. The participant opens the link and lands directly in the joining flow. They provide their name, email and questionnaire responses. They should not need to enter the group passkey again because the invitation link already identifies the group.

**Option B: Enter a passkey**

A participant who visits the website independently selects the “Already in a group” entry point, enters the group's six-digit passkey, provides their name and email, and completes the questionnaire.

The passkey belongs to the group and is shared by all participants. It is not a unique passkey for each person.

### Landing page

The landing page should make the two primary actions clear:

- Create a new group.
- Already in a group? Enter passkey.

Keep the entry experience simple and direct.

## 5. Group lifecycle and assignment logic

### Three-day joining window

When a group is created, the organizer has three days to finalize the participant list.

During this period:

- Participants can join.
- The organizer can monitor participation.
- The organizer can manage the participant list.
- Invitations and reminders can be sent.

At the end of the three-day window:

- The group locks automatically.
- No new participants can join through the normal flow.
- Secret Santa assignments are generated.
- Assignments cannot be changed through the normal organizer flow.

The organizer should be clearly informed of the deadline when creating the group. The countdown and lock state should be visible in Organizer mode.

### Assignment requirements

The assignment logic must work for both odd-numbered and even-numbered groups.

Every valid group must satisfy all of these rules:

- Each participant gives to exactly one person.
- Each participant receives from exactly one person.
- Nobody is assigned themselves.
- Every participant has exactly one recipient.
- Assignments remain private.

A circular shuffle is sufficient for the MVP:

1. Randomly shuffle the participant list.
2. Assign each person to the next person in the shuffled list.
3. Assign the final person to the first person in the list.

This creates one closed loop and works for any group size of two or more, whether the number of participants is odd or even. A group with fewer than two participants cannot produce a valid assignment.

Do not use naive independent random assignment. It can create self-assignments or leave participants without a recipient.

## 6. Participant questionnaire

The questionnaire is central to the product's value. It should help the system understand each recipient well enough to suggest gifts that feel personal, without feeling like a long survey.

Potential questions include:

- What are your hobbies and interests?
- What do you enjoy doing in your free time?
- What are you passionate about?
- What is your personal style?
- What are some things you would love to receive?
- What kinds of gifts do you dislike?
- What do you already own that someone might otherwise gift you?
- Do you have any restrictions or preferences?
- What types of gifts do you prefer?
- Is there anything else your Secret Santa should know?

This is a candidate question set, not a finalized questionnaire. Keep the final version short and engaging.

Participants must also provide a delivery address so their assigned Santa can ship the gift directly without having to ask them for it.

## 7. Wishlist and AI-assisted gift recommendations

After completing the questionnaire, participants should be able to build a wishlist using two complementary paths.

### AI-generated recommendations

The AI should interpret the participant's questionnaire answers and suggest relevant gift ideas. Recommendations should take the recipient's interests, preferences, dislikes, existing possessions and the group's maximum gift budget into account.

For example, a participant who loves coffee, already owns a coffee machine and enjoys experimenting with coffee should not simply be recommended another generic coffee machine. More thoughtful suggestions might include a specialty coffee subscription, a coffee cupping kit, a precision coffee scale or a distinctive coffee accessory.

The goal is to avoid obvious, repetitive or redundant suggestions.

### Manual wishlist

Participants remain in control of their wishlist. They should be able to:

- Add an item.
- Edit an item.
- Remove an item.
- Combine their own ideas with AI-generated suggestions.

The wishlist should not force participants to accept AI suggestions.

### Real, purchasable products

A key product differentiator is the ability to move beyond generic gift ideas and recommend real products people can buy.

Potential marketplaces include Amazon, Flipkart, Meesho and Myntra.

Ideally, a product recommendation should contain:

- Product image.
- Product name.
- Approximate price.
- Marketplace.
- Direct product link.
- A short explanation of why the product suits the recipient.

This is an unresolved technical challenge. Possible discovery approaches include marketplace APIs, affiliate product feeds, product search APIs or other legitimate product-discovery services.

**AI must not invent product names, prices, availability or URLs.** Product information should come from a reliable source and be presented as current only when it has been verified. The group's maximum gift budget should influence the recommendations.

## 8. The Gifter experience

The Gifter screen is the primary participant experience after assignments are generated. It should give the assigned Santa enough information to choose and deliver a thoughtful gift without needing to contact the recipient.

### Recipient information

Show:

- Recipient's name.
- Relevant questionnaire insights.
- Interests and preferences.

Only information relevant to the assigned recipient should be exposed.

### Wishlist and recommendations

Show:

- Items manually added by the recipient.
- AI-generated gift suggestions.
- Real product recommendations, images and purchase links where available.

### Delivery information

Show the recipient's delivery address with an easy copy-address action.

A participant must only be able to access the person assigned to them. They must never be able to see other participants' assignments by changing a URL or manipulating frontend data. This must be enforced by the backend, not just hidden in the interface.

## 9. Organizer dashboard

The organizer dashboard has two modes.

### Organizer mode

Show:

- Group name and details.
- Six-digit group passkey.
- Three-day countdown.
- Participant list and joining status.
- Participant management while the group is open.
- Invitation and reminder actions.
- Group lock status.

### Gifter mode

Show the organizer's own assigned recipient, that recipient's wishlist, recommendations and delivery address. The organizer's Gifter experience should follow the same privacy rules as every other participant.

### After the group locks

The organizer cannot:

- Add participants.
- Remove participants.
- Change assignments.

The organizer can:

- Resend an access link to an individual participant.
- Resend access links to the entire group.

Resending access links must never generate new assignments.

## 10. Authentication and returning participants

The initial direction is email-based authentication rather than traditional passwords. Email is already required for invitations and assignment notifications.

A potential magic-link flow:

1. The participant enters their email.
2. The system sends a secure login link.
3. The participant clicks the link to authenticate.
4. The system retrieves their existing participant record.

Returning participants should not need to complete the questionnaire again. Their existing questionnaire responses, wishlist, AI recommendations and group participation information should be retrieved.

Magic links must expire appropriately, be difficult to guess or reuse, and never expose recipient assignments to unauthorized users. The exact authentication provider and implementation have not been finalized.

## 11. Transactional email

Brevo is the initial choice discussed for transactional email. The backend should trigger emails in response to product events.

### Group invitation

Sent by the organizer. It should contain the group name, invitation message, personalized deep link and joining instructions.

### Joining confirmation

Sent after a participant successfully joins. It should confirm registration, identify the group and explain when assignments will be generated.

### Assignment notification

Sent automatically after the group locks and assignments are generated. It should contain a personalized link to the Gifter screen, instructions for viewing the assigned recipient and a reminder of the gift budget.

The email should not reveal sensitive recipient information unnecessarily. Recipient details should be available inside the authenticated Gifter experience.

### Resend access

Triggered by the organizer for an individual participant or the whole group. It should return participants to their existing Gifter experience without changing assignments.

Email templates and final copy have not been designed yet.

## 12. Privacy and security requirements

Trust is essential because the product handles personal preferences, delivery addresses and private assignments.

Non-negotiable requirements:

- A participant can only access their own assigned recipient.
- The organizer cannot automatically inspect everyone else's assignments.
- Backend authorization must protect assignments and participant data. Frontend-only restrictions are insufficient.
- Delivery addresses must be stored securely and be accessible only to the assigned gifter for fulfilling the gift.
- Email notifications should not expose sensitive recipient information unnecessarily.
- Magic links must be secure and expire appropriately.
- Resending access links must not regenerate or alter assignments.
- Questionnaire responses and delivery addresses should not be retained longer than necessary.

The exact retention and deletion policy is still an open decision and must be settled before launch.

## 13. Initial technology direction

The following stack was discussed as an initial direction. It is not a final technical constraint. Database, authentication and hosting decisions remain open, and alternatives should be evaluated for simplicity, security and cost before implementation.

| Layer | Initial direction | Status |
|---|---|---|
| Frontend | React | Proposed |
| Build tool | Vite | Proposed |
| Styling | Tailwind CSS | Present in the initial frontend setup |
| Backend | Node.js | Proposed; not confirmed as implemented |
| Transactional email | Brevo | Selected direction; integration not confirmed |
| Database | To be decided | Open |
| Authentication | Email magic links | Under consideration |
| Hosting | Hostinger or another affordable option | Open |
| Version control | GitHub | In use |
| Development environment | Cursor on macOS | Current workflow |

The product is intended to be a responsive website, not a native mobile app.

Do not change the stack simply because another tool is popular. Explain the trade-offs and choose the simplest suitable approach.

## 14. Scope and possible future expansion

The first release should focus on the Christmas Secret Santa journey: group creation, participant onboarding, questionnaire and wishlist, automatic assignments, private Gifter experience, delivery information and the supporting email flows.

Birthdays, anniversaries, office gifting and other occasions are possible future directions. Do not let those use cases complicate the initial MVP.

Potential business questions, such as whether the product should remain free or eventually earn affiliate commissions, should be explored after the core experience is validated.

## 15. Open product, technical and business questions

These decisions are unresolved. They should be tackled in priority order as the MVP is designed and built, rather than all at once.

### Product and UX

1. What happens if a participant withdraws during the three-day joining window?
2. What happens if someone joins but never completes the questionnaire?
3. Should the organizer be able to extend the three-day deadline?
4. Should the organizer be able to trigger assignments manually before the deadline?
5. What happens if an invitation email bounces?
6. Can participants update their wishlist after assignments are generated?
7. Should delivery addresses be deleted automatically after the gifting event?

### Technical

1. Which database should be used?
2. What is the simplest secure authentication solution?
3. How should real ecommerce products be retrieved?
4. How should AI recommendations be generated and stored?
5. What is the expected AI cost per participant?
6. How should duplicate participants and email abuse be prevented?
7. How should participant data and assignments be secured?
8. How should expired magic links and email delivery failures be handled?

### Business

1. Should the product remain free initially?
2. Could affiliate commissions eventually generate revenue?
3. Should the product expand beyond Secret Santa?
4. How can users be acquired for a highly seasonal use case?

## 16. Current implementation status

The project was previously started as a React website using Cursor. The current default-branch repository snapshot is still at an early scaffold stage:

- The repository has an initial frontend structure.
- Tailwind CSS dependencies are present in the root package configuration.
- The current frontend App component displays a simple Smart Secret Santa heading.
- A working backend, database, authentication, assignment service, AI recommendation system, product discovery integration and Brevo automation are not established by the current scaffold.

The project was paused because Secret Santa is highly seasonal. It can be resumed, but the existing code must be inspected before assuming any feature is complete or that the implementation matches every product decision in this README.

**Keep product intent separate from implementation status.** Update this section as real capabilities are built and tested.

## 17. Recommended development approach

Build incrementally. Avoid spending weeks designing a large system before getting the core experience working.

A sensible sequence is:

1. Revisit and validate the MVP scope.
2. Identify the riskiest product and technical assumptions.
3. Finalize the primary user journeys and edge cases.
4. Define the data model and system architecture.
5. Build the frontend and backend incrementally.
6. Implement authentication.
7. Implement and test the assignment algorithm.
8. Build the questionnaire, wishlist and Gifter experience.
9. Integrate AI-assisted recommendations.
10. Evaluate and integrate reliable real-product discovery.
11. Set up Brevo transactional email automation.
12. Test edge cases, privacy and security.
13. Deploy and validate a working MVP.

Before writing code, make sure the product behaviour and reasons behind the decisions are understood. During implementation, work one step at a time, identify exact files to change, explain technical decisions in beginner-friendly language, provide complete code where appropriate, and test each increment.

Avoid overengineering. Prioritize a genuinely useful, secure MVP.
