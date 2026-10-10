from typing import List
from ingestion.schemas import OrderBookLevel, DepthWalkResult

class DepthWalker:
    """Simulates executing orders against actual order book depth levels to calculate executable fill prices and slippage."""

    @staticmethod
    def walk_asks(asks: List[OrderBookLevel], target_dollar_amount: float) -> DepthWalkResult:
        """
        Simulates buying YES or NO contracts up to target_dollar_amount.
        Asks are sorted ascending by price (cheapest first).
        """
        if not asks or target_dollar_amount <= 0:
            return DepthWalkResult(
                target_size=target_dollar_amount,
                filled_size=0,
                average_price=0.0,
                total_cost=0.0,
                slippage=0.0,
                levels_walked=0,
                fully_executable=False
            )

        top_price = asks[0].price
        remaining_budget = target_dollar_amount
        total_contracts_bought = 0.0
        total_cost = 0.0
        levels_walked = 0

        for level in asks:
            if remaining_budget <= 0:
                break
            
            levels_walked += 1
            max_cost_at_level = level.price * level.size

            if remaining_budget >= max_cost_at_level:
                # Fill entire level
                total_contracts_bought += level.size
                total_cost += max_cost_at_level
                remaining_budget -= max_cost_at_level
            else:
                # Partial fill of level
                contracts_bought = remaining_budget / level.price
                total_contracts_bought += contracts_bought
                total_cost += remaining_budget
                remaining_budget = 0
                break

        if total_contracts_bought == 0:
            avg_price = top_price
        else:
            avg_price = round(total_cost / total_contracts_bought, 4)

        slippage_pct = round(((avg_price - top_price) / top_price) * 100.0, 2) if top_price > 0 else 0.0
        fully_executable = (remaining_budget <= 0.01)

        return DepthWalkResult(
            target_size=target_dollar_amount,
            filled_size=round(total_contracts_bought, 2),
            average_price=avg_price,
            total_cost=round(total_cost, 2),
            slippage=max(0.0, slippage_pct),
            levels_walked=levels_walked,
            fully_executable=fully_executable
        )
