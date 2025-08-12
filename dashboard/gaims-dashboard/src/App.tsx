import React from 'react';

import { useState, useEffect, useRef } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  ChevronDown,
  MessageSquare,
  LineChart as LineChartIcon,
} from "lucide-react";

// This is the core parsing function adapted from your original JS code.
// It uses regular expressions to find and extract relevant information from the log string.
const parseGameLogs = (logData) => {
  const rounds = [];
  const lines = logData.split("\n");
  let currentRoundData = null;
  let currentInteraction = null;

  const roundRegex = /^INFO:gaims.gym_env:Round: (\d+)/;
  const utilityRegex = /^INFO:gaims.gym_env:Player Utility: ([\d.\-]+)/;
  const payoffRegex =
    /^INFO:gaims.gym_env:Payoff Matrix:\s*\n(tensor\(\[\[\[.*\]\]\]\))/s;
  const interactionStartRegex = /^INFO:gaims.agents.models:--> (.*?): (.*?):/;
  const thoughtsRegex =
    /Given the current state, game rules, and your past observations, write down your thoughts, plans, and any new observations\.\nINFO:gaims\.agents\.models:.*? -->: ([\s\S]*?)(?=\nWhich action will you choose?|You may now send a message|INFO:gaims\.gym_env:Agent \d+ took action)/;
  const messageRegex =
    /Here are the messages you received:\nPlayer \d+ said: ([\s\S]*?)\n\nGiven these messages, game rules, and prior information,/;
  const actionRegex = /^INFO:gaims.gym_env:Agent (\d+) took action (\d+)/;
  const rewardRegex = /^INFO:gaims.gym_env:Reward: tensor\(\[(.*?)\]\)/;
  const nashRegex = /^INFO:gaims.gym_env:Nash Equilibria: \[(.*?)\]/;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (roundRegex.test(line)) {
      if (currentRoundData) {
        if (currentInteraction)
          currentRoundData.interactions.push(currentInteraction);
        rounds.push(currentRoundData);
      }
      currentRoundData = {
        round: parseInt(line.match(roundRegex)[1]),
        playerUtility: null,
        payoffMatrix: null,
        interactions: [],
        actions: [],
        reward: null,
        nashEquilibria: null,
      };
      currentInteraction = null;
    }

    if (currentRoundData) {
      if (utilityRegex.test(line)) {
        currentRoundData.playerUtility = parseFloat(
          line.match(utilityRegex)[1]
        );
      }

      const remainingLog = lines.slice(i).join("\n");
      const payoffMatch = remainingLog.match(payoffRegex);
      if (payoffMatch && !currentRoundData.payoffMatrix) {
        currentRoundData.payoffMatrix = payoffMatch[1];
      }

      if (interactionStartRegex.test(line)) {
        if (currentInteraction) {
          currentRoundData.interactions.push(currentInteraction);
        }
        const match = line.match(interactionStartRegex);
        currentInteraction = {
          player: match[1],
          role: match[2],
          thoughts: null,
          receivedMessage: null,
        };
      }

      if (currentInteraction) {
        const thoughtsMatch = remainingLog.match(thoughtsRegex);
        if (thoughtsMatch && !currentInteraction.thoughts) {
          currentInteraction.thoughts = thoughtsMatch[1].trim();
        }

        const messageMatch = remainingLog.match(messageRegex);
        if (messageMatch && !currentInteraction.receivedMessage) {
          currentInteraction.receivedMessage = messageMatch[1].trim();
        }
      }

      if (actionRegex.test(line)) {
        const match = line.match(actionRegex);
        currentRoundData.actions.push({
          player: parseInt(match[1]),
          action: parseInt(match[2]),
        });
      } else if (rewardRegex.test(line)) {
        const rewardString = line.match(rewardRegex)[1];
        currentRoundData.reward = rewardString
          .split(", ")
          .map((s) => parseFloat(s));
      } else if (nashRegex.test(line)) {
        const nashString = line.match(nashRegex)[1];
        currentRoundData.nashEquilibria = nashString
          .split("), (")
          .map((s) => `(${s.replace(/[()]/g, "")})`);
      }
    }
  }

  if (currentRoundData) {
    if (currentInteraction)
      currentRoundData.interactions.push(currentInteraction);
    rounds.push(currentRoundData);
  }

  return rounds;
};

// Dummy log content to pre-fill the textarea
// Open log
const dummyLogContent = 

// Minimal placeholder components for shadcn/ui to make the app runnable.
// In a real project, these would be imported from a UI library.
const Card = ({ className, ...props }) => (
  <div
    className={`rounded-lg border bg-card text-card-foreground shadow-sm ${className}`}
    {...props}
  />
);
const CardHeader = ({ className, ...props }) => (
  <div className={`flex flex-col space-y-1.5 p-6 ${className}`} {...props} />
);
const CardTitle = ({ className, ...props }) => (
  <h3
    className={`text-2xl font-semibold leading-none tracking-tight ${className}`}
    {...props}
  />
);
const CardContent = ({ className, ...props }) => (
  <div className={`p-6 pt-0 ${className}`} {...props} />
);
const Button = ({ className, ...props }) => (
  <button
    className={`inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 h-9 px-4 py-2 ${className}`}
    {...props}
  />
);
const Textarea = ({ className, ...props }) => (
  <textarea
    className={`flex min-h-[60px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
    {...props}
  />
);

const CollapsibleContext = React.createContext(false);
const Collapsible = ({ className, children, ...props }) => {
  const [isOpen, setIsOpen] = useState(false);
  const value = { isOpen, setIsOpen };
  return (
    <CollapsibleContext.Provider value={value}>
      <div className={`space-y-2 ${className}`} {...props}>
        {children}
      </div>
    </CollapsibleContext.Provider>
  );
};
const CollapsibleTrigger = ({ className, children, ...props }) => {
  const { isOpen, setIsOpen } = React.useContext(CollapsibleContext);
  return (
    <button
      onClick={() => setIsOpen(!isOpen)}
      className={`flex items-center justify-between w-full p-2 rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200 transition-colors ${className}`}
      {...props}
    >
      {children}
      <ChevronDown
        className={`h-4 w-4 collapsible-icon transition-transform duration-300 ${
          isOpen ? "rotate-180" : ""
        }`}
      />
    </button>
  );
};
const CollapsibleContent = ({ className, children, ...props }) => {
  const { isOpen } = React.useContext(CollapsibleContext);
  return isOpen ? (
    <div className={`${className}`} {...props}>
      {children}
    </div>
  ) : null;
};

// Main React App component
export default function App() {
  const [logData, setLogData] = useState(DUMMY_LOG_CONTENT);
  const [parsedRounds, setParsedRounds] = useState([]);

  // Parse the dummy data on initial load
  useEffect(() => {
    setParsedRounds(parseGameLogs(DUMMY_LOG_CONTENT));
  }, []);

  const handleParse = () => {
    setParsedRounds(parseGameLogs(logData));
  };

  const getChartData = () => {
    return parsedRounds.map((round) => {
      const data = {
        name: `Round ${round.round}`,
      };
      if (round.reward && round.reward.length > 0) {
        data.player0 = round.reward[0];
        if (round.reward.length > 1) {
          data.player1 = round.reward[1];
        }
      }
      return data;
    });
  };

  return (
    <div className="flex flex-col min-h-screen bg-gray-50 text-gray-900 font-sans p-4 sm:p-8 space-y-8">
      <header className="text-center">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-gray-800">
          Game Log Dashboard
        </h1>
        <p className="mt-2 text-md sm:text-lg text-gray-600">
          Paste your log data and click parse to visualize the game rounds.
        </p>
      </header>

      <main className="flex-1 space-y-8 max-w-7xl mx-auto w-full">
        <Card className="shadow-lg border-gray-200">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-xl font-semibold">
              <MessageSquare className="h-6 w-6 text-indigo-500" />
              <span>Log Input</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Textarea
              className="min-h-[200px] font-mono text-sm resize-y"
              placeholder="Paste your game log data here..."
              value={logData}
              onChange={(e) => setLogData(e.target.value)}
            />
            <Button
              onClick={handleParse}
              className="w-full bg-indigo-600 text-white hover:bg-indigo-700 transition-colors"
            >
              Parse Logs
            </Button>
          </CardContent>
        </Card>

        {parsedRounds.length > 0 && (
          <Card className="shadow-lg border-gray-200">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-xl font-semibold">
                <LineChartIcon className="h-6 w-6 text-teal-500" />
                <span>Player Rewards</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="w-full h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={getChartData()}
                    margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="player0"
                      stroke="#8884d8"
                      name="Player 0 Reward"
                    />
                    <Line
                      type="monotone"
                      dataKey="player1"
                      stroke="#82ca9d"
                      name="Player 1 Reward"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        )}

        {parsedRounds.length > 0 && (
          <div className="space-y-4">
            {parsedRounds.map((roundData, index) => (
              <Card key={index} className="shadow-lg border-gray-200">
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2 text-xl font-semibold text-gray-800">
                    <span>Round {roundData.round}</span>
                    <span className="text-sm font-normal text-gray-500 ml-auto">
                      Player Utility:{" "}
                      {roundData.playerUtility !== null
                        ? roundData.playerUtility.toFixed(2)
                        : "N/A"}
                    </span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <h3 className="font-semibold text-gray-700">Actions</h3>
                      <ul className="list-disc list-inside mt-1 space-y-1 text-sm text-gray-600">
                        {roundData.actions.map((action, actionIndex) => (
                          <li key={actionIndex}>
                            Agent {action.player} took action {action.action}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-700">Rewards</h3>
                      <p className="mt-1 text-sm text-gray-600">
                        {roundData.reward
                          ? roundData.reward
                              .map((r, i) => `Player ${i}: ${r}`)
                              .join(", ")
                          : "N/A"}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <h3 className="font-semibold text-gray-700">
                        Nash Equilibria
                      </h3>
                      <p className="mt-1 text-sm text-gray-600">
                        {roundData.nashEquilibria
                          ? roundData.nashEquilibria.join(", ")
                          : "N/A"}
                      </p>
                    </div>
                    <div>
                      <h3 className="font-semibold text-gray-700">
                        Payoff Matrix
                      </h3>
                      <pre className="mt-1 p-2 bg-gray-100 rounded-md text-xs font-mono overflow-x-auto text-gray-700">
                        {roundData.payoffMatrix || "N/A"}
                      </pre>
                    </div>
                  </div>

                  <Collapsible>
                    <CollapsibleTrigger>
                      <h4 className="font-semibold text-sm flex items-center space-x-2">
                        <MessageSquare className="w-4 h-4" />
                        <span>View Interactions</span>
                      </h4>
                    </CollapsibleTrigger>
                    <CollapsibleContent className="mt-2 space-y-4">
                      {roundData.interactions.length > 0 ? (
                        roundData.interactions.map(
                          (interaction, interactionIndex) => (
                            <Card
                              key={interactionIndex}
                              className="p-4 bg-white border border-gray-200"
                            >
                              <h5 className="font-bold text-sm text-indigo-600">
                                {interaction.player} ({interaction.role})
                              </h5>
                              <div className="space-y-2 text-sm text-gray-600 mt-2">
                                {interaction.thoughts && (
                                  <p>
                                    <strong>Thoughts:</strong>{" "}
                                    {interaction.thoughts}
                                  </p>
                                )}
                                {interaction.receivedMessage && (
                                  <p>
                                    <strong>Received Message:</strong>{" "}
                                    {interaction.receivedMessage}
                                  </p>
                                )}
                              </div>
                            </Card>
                          )
                        )
                      ) : (
                        <p className="text-center text-gray-500 text-sm">
                          No interactions found for this round.
                        </p>
                      )}
                    </CollapsibleContent>
                  </Collapsible>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
