# (C) Copyright 2025 Anemoi contributors.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.

from typing import Any
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Union


class Rule:

    def __init__(self, match: Dict[str, Any], result: Any):
        """Initialize a Rule object.

        Parameters
        ----------
        match : Dict[str, Any]
            A dictionary defining the conditions for the rule to match.
        result : Any
            The result to return if the rule matches.
        """
        self._match = match
        self._result = result

    def match(self, obj: Mapping[str, Any]) -> bool:
        """Check if the rule matches the given object.

        Parameters
        ----------
        obj : Mapping[str, Any]
            The object to check against the rule's conditions.

        Returns
        -------
        bool
            True if the rule matches, False otherwise.
        """
        for key, value in self._match.items():
            if key not in obj or obj[key] != value:
                return False

        return True

    @property
    def result(self) -> Any:
        return self._result

    @property
    def condition(self) -> Dict[str, Any]:
        return self._match


class RuleSet:

    def __init__(self, rules: List[Union[Rule, Dict[str, Any], List[Any]]]):
        """Initialize a RuleSet object.

        Parameters
        ----------
        rules : List[Union[Rule, Dict[str, Any], List[Any]]]
            A list of rules, where each rule can be a Rule object, a dictionary with
            'match' and 'result' keys, or a list with two elements (match and result).
        """
        assert isinstance(rules, list), "rules must be a list"

        self.rules: List[Rule] = []

        for rule in rules:
            if isinstance(rule, Rule):
                self.rules.append(rule)
                continue

            if isinstance(rule, dict):

                assert len(rule) == 2, "Rule dictionary must contain exactly two key-value pair."

                match = rule.get("match")
                if match is None:
                    raise ValueError("Rule dictionary must contain a 'match' key.")

                result = rule.get("result")
                if result is None:
                    raise ValueError("Rule dictionary must contain a 'result' key.")

                self.rules.append(Rule(match, result))
                continue

            if isinstance(rule, list):
                assert len(rule) == 2, "Rule list must contain exactly two elements."
                match = rule[0]
                result = rule[1]
                self.rules.append(Rule(match, result))
                continue

            raise ValueError(
                "Rule must be either a Rule object, a dictionary with 'match' and 'result' keys, or a list with two elements."
            )

    @classmethod
    def from_list(cls, rules: List[Any]) -> "RuleSet":
        """Create a RuleSet from a list of rules.

        Parameters
        ----------
        rules : List[Any]
            A list of rules to initialize the RuleSet.

        Returns
        -------
        RuleSet
            A new RuleSet object.
        """
        return cls(rules)

    @classmethod
    def from_files(cls, path: str) -> "RuleSet":
        """Create a RuleSet from a file.

        Parameters
        ----------
        path : str
            The path to the file containing the rules. Supported formats are .json and .yaml/.yml.

        Returns
        -------
        RuleSet
            A new RuleSet object.

        Raises
        ------
        ValueError
            If the file format is unsupported.
        """
        if path.endswith(".json"):
            import json

            with open(path, "r") as f:
                return cls.from_list(json.load(f))

        if path.endswith(".yaml") or path.endswith(".yml"):
            import yaml

            with open(path, "r") as f:
                return cls.from_list(yaml.safe_load(f))

        raise ValueError("Unsupported file format. Supported formats are .json and .yaml/.yml.")

    @classmethod
    def from_any(cls, rules: Union[str, List[Any]]) -> "RuleSet":
        """Create a RuleSet from a list or a file path.

        Parameters
        ----------
        rules : Union[str, List[Any]]
            The rules to initialize the RuleSet, either as a list or a file path.

        Returns
        -------
        RuleSet
            A new RuleSet object.

        Raises
        ------
        ValueError
            If the rules format is unsupported.
        """
        if isinstance(rules, str):
            return cls.from_files(rules)

        if isinstance(rules, list):
            return cls.from_list(rules)

        raise ValueError("Unsupported rules format. Must be a list or a file path.")

    def match(self, obj: Mapping[str, Any], strategy: str = "first-match") -> Optional[Rule]:
        """Match an object against the rules in the RuleSet.

        Parameters
        ----------
        obj : Mapping[str, Any]
            The object to match against the rules.
        strategy : str, optional
            The matching strategy to use. Currently, only 'first-match' is supported.

        Returns
        -------
        Optional[Rule]
            The first matching rule, or None if no match is found.

        Raises
        ------
        AssertionError
            If an unsupported strategy is provided.
        """
        assert strategy == "first-match", "Only 'first-match' strategy is supported for now."
        for rule in self.rules:
            if rule.match(obj):
                return rule

        return None

    def __iter__(self) -> iter:
        """Return an iterator over the rules in the RuleSet.

        Returns
        -------
        iter
            An iterator over the Rule objects in the RuleSet.
        """
        return iter(self.rules)
