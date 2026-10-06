package mbla

import (
	"fmt"
	"testing"
)

func syntheticPolicy(size int, owner string) Policy {
	policy := Policy{}
	for index := range size {
		policy = policy.Add(MustParse(fmt.Sprintf("github:issue.read:%s/repo%d#%d", owner, index, index)))
	}
	return policy
}

func BenchmarkCheckAttenuation(b *testing.B) {
	for _, size := range []int{4, 16, 64, 256} {
		child := syntheticPolicy(size, "acme")
		parent := syntheticPolicy(size, "acme")
		b.Run(fmt.Sprintf("atoms=%d", size), func(b *testing.B) {
			for range b.N {
				CheckAttenuation(child, parent)
			}
		})
	}
}
